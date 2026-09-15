/* Bo Åke Adamsson site behaviour.
 *
 * Every page here is a real, statically generated HTML document: the gallery,
 * each artwork, and the about page all render fully without JavaScript, which
 * is what search engines index. This file layers instant in-page navigation on
 * top of that, so clicking around never costs a round trip, and the URL in the
 * address bar stays a real one that can be shared and bookmarked.
 */
(function () {
    'use strict';

    document.documentElement.classList.remove('no-js');

    var DATA = window.ARTWORKS || [];
    var BASE = '/images/opt/';
    var FILTER_TITLES = {
        all: 'Selected Works',
        oil: 'Oil Paintings',
        graphics: 'Graphics',
        sculpture: 'Bronze Sculptures'
    };
    var FILTER_PATH = { all: '/', oil: '/oil/', graphics: '/graphics/', sculpture: '/sculpture/' };
    var SIZES_GALLERY = '(max-width:700px) 92vw, (max-width:1100px) 46vw, 30vw';
    var SIZES_WORK = '(max-width:900px) 92vw, 55vw';

    var byId = function (id) { return document.getElementById(id); };
    var bySlug = {};
    DATA.forEach(function (a) { bySlug[a.slug] = a; });

    /* ---------- helpers shared with the build script ---------- */

    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* A dimensions field counts as recorded only if it holds more than a
       dash or a blank; the catalogue has used several placeholders over time. */
    function hasSize(d) {
        return !!(d && d.replace(/[\s\u2010-\u2015-]/g, '') !== '');
    }

    function priceDisplay(price, type) {
        if (type === 'sculpture' || price > 10000) return 'Price on Request';
        return '€' + price.toLocaleString('en-US');
    }

    function srcset(stem, widths, ext) {
        return widths.map(function (w) {
            return BASE + stem + '-' + w + '.' + ext + ' ' + w + 'w';
        }).join(', ');
    }

    /* Builds the same <picture> markup the build script emits, so a
       JS-rendered image is byte-for-byte what a crawler would have seen. */
    function picture(art, alt, sizes, eager) {
        var widths = art.widths;
        var fallback = widths[widths.length - 1];
        var ratio = art.w && art.h ? ' width="' + art.w + '" height="' + art.h + '"' : '';
        return '<picture>' +
            '<source type="image/avif" srcset="' + srcset(art.stem, widths, 'avif') + '" sizes="' + sizes + '">' +
            '<source type="image/webp" srcset="' + srcset(art.stem, widths, 'webp') + '" sizes="' + sizes + '">' +
            '<img src="' + BASE + art.stem + '-' + fallback + '.jpg"' +
            ' srcset="' + srcset(art.stem, widths, 'jpg') + '" sizes="' + sizes + '"' +
            ratio + ' alt="' + escapeHtml(alt) + '"' +
            (eager ? ' fetchpriority="high" decoding="async"' : ' loading="lazy" decoding="async"') +
            '></picture>';
    }

    /* ---------- progressive reveal ---------- */

    /* An image that is already in the browser cache fires no load event, so
       check complete() first, otherwise cached images would stay invisible. */
    function watchImages(root) {
        [].forEach.call((root || document).querySelectorAll('.ph'), function (ph) {
            var img = ph.querySelector('img');
            if (!img) return;
            if (img.complete && img.naturalWidth > 0) {
                ph.classList.add('ready');
            } else {
                img.addEventListener('load', function () { ph.classList.add('ready'); });
                img.addEventListener('error', function () { ph.classList.add('ready'); });
            }
        });
    }

    var revealObserver = null;
    if ('IntersectionObserver' in window) {
        revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (!e.isIntersecting) return;
                e.target.classList.add('seen');
                revealObserver.unobserve(e.target);
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    }

    function watchReveals(root) {
        [].forEach.call((root || document).querySelectorAll('.reveal:not(.seen)'), function (el) {
            if (revealObserver) revealObserver.observe(el);
            else el.classList.add('seen');
        });
    }

    /* ---------- gallery ---------- */

    var currentFilter = (window.PAGE && window.PAGE.filter) || 'all';

    function galleryCard(art) {
        var p = priceDisplay(art.price, art.type);
        var priceHtml = p === 'Price on Request'
            ? '<span class="price request">On Request</span>'
            : '<span class="price">' + p + '</span>';
        var dims = [hasSize(art.dimensions) ? art.dimensions : null, art.year]
            .filter(Boolean).join(' · ');
        var alt = art.title + ', ' + art.typeName.toLowerCase() + ' by Bo Åke Adamsson';
        return '<a class="piece reveal" href="/work/' + art.slug + '/" data-slug="' + art.slug + '"' +
            ' aria-label="View ' + escapeHtml(art.title) + ' in detail">' +
            '<figure class="ph">' + picture(art, alt, SIZES_GALLERY) +
            '<span class="tag">' + escapeHtml(art.typeName) + '</span></figure>' +
            '<figcaption><div class="row1"><h3>' + escapeHtml(art.title) + '</h3>' + priceHtml + '</div>' +
            '<div class="dims">' + escapeHtml(dims) + '</div></figcaption></a>';
    }

    var galleryFilter = null;   // which filter the DOM currently holds

    function counts() {
        var c = { all: DATA.length, oil: 0, graphics: 0, sculpture: 0 };
        DATA.forEach(function (a) { if (c[a.type] !== undefined) c[a.type]++; });
        return c;
    }

    function buildFilterBar() {
        var bar = document.querySelector('.filter-bar');
        if (!bar || bar.children.length) return;
        var c = counts();
        bar.innerHTML = Object.keys(FILTER_PATH).map(function (k) {
            return '<a href="' + FILTER_PATH[k] + '" data-filter="' + k + '" role="button">' +
                (k === 'all' ? 'All Works' : FILTER_TITLES[k]) +
                '<span class="count">' + c[k] + '</span></a>';
        }).join('');
    }

    function renderGallery(filter) {
        currentFilter = filter;
        var gallery = byId('gallery');
        var title = byId('collection-title');
        if (title) title.textContent = FILTER_TITLES[filter] || FILTER_TITLES.all;

        buildFilterBar();
        [].forEach.call(document.querySelectorAll('.filter-bar [data-filter]'), function (b) {
            var on = b.dataset.filter === filter;
            b.classList.toggle('active', on);
            if (on) b.setAttribute('aria-current', 'page');
            else b.removeAttribute('aria-current');
        });

        if (!gallery || galleryFilter === filter) return;

        var list = filter === 'all' ? DATA : DATA.filter(function (a) { return a.type === filter; });
        gallery.innerHTML = list.length
            ? list.map(galleryCard).join('')
            : '<p class="empty">No works in this category at the moment.</p>';
        galleryFilter = filter;
        watchImages(gallery);
        watchReveals(gallery);
    }

    /* ---------- artwork detail ---------- */

    function renderWork(slug) {
        var art = bySlug[slug];
        if (!art) return false;

        var idx = DATA.indexOf(art);
        var prev = DATA[(idx - 1 + DATA.length) % DATA.length];
        var next = DATA[(idx + 1) % DATA.length];
        var setHref = function (id, href) {
            var el = byId(id);
            if (el) el.setAttribute('href', href);
        };
        setHref('work-prev', '/work/' + prev.slug + '/');
        setHref('work-next', '/work/' + next.slug + '/');
        setHref('work-back', FILTER_PATH[currentFilter] || '/');

        var body = byId('work-body');
        if (body) body.innerHTML = workBody(art);
        watchImages(body);
        return true;
    }

    function workBody(art) {
        var p = priceDisplay(art.price, art.type);
        var onRequest = p === 'Price on Request';
        var rows = [['Medium', art.typeName]];
        // Not every work has a recorded size; say so rather than drop the row.
        rows.push(['Dimensions', hasSize(art.dimensions) ? art.dimensions : 'On request']);
        rows.push(['Year', art.year]);
        var specRows = rows.map(function (kv) {
            return '<div class="spec-row"><span class="k">' + kv[0] + '</span>' +
                '<span class="v">' + escapeHtml(kv[1]) + '</span></div>';
        }).join('') +
            '<div class="spec-row"><span class="k">Price</span>' +
            '<span class="v price-lg">' + p + '</span></div>';

        var alt = art.title + ', ' + art.typeName.toLowerCase() + ' by Bo Åke Adamsson';
        var desc = art.description ? '<p class="work-desc">' + escapeHtml(art.description) + '</p>' : '';
        var avail = onRequest
            ? 'This work is available. Send an inquiry below and the studio will respond personally with the price and delivery details.'
            : 'This work is available for purchase. Send an inquiry below and the studio will respond personally to arrange the details.';

        return '<div class="work-figure ph">' + picture(art, alt, SIZES_WORK, true) + '</div>' +
            '<div class="work-info">' +
            '<div class="eyebrow">' + escapeHtml(art.typeName) + '</div>' +
            '<h1>' + escapeHtml(art.title) + '</h1>' +
            '<div class="spec-table">' + specRows + '</div>' + desc +
            '<div class="avail-note"><span class="rd"></span><span>' + avail + '</span></div>' +
            inquiryForm(art) + '</div>';
    }

    function inquiryForm(art) {
        return '<form class="inquiry-form" data-inquiry="' + escapeHtml(art.title) + '">' +
            '<h3>Inquire about this work</h3>' +
            '<p class="sub">Your message goes straight to Bo Åke’s studio. No galleries, no middlemen.</p>' +
            '<div class="form-group"><label for="inq-name">Your Name</label>' +
            '<input type="text" id="inq-name" name="name" required placeholder="Enter your full name" autocomplete="name"></div>' +
            '<div class="form-group"><label for="inq-email">Email Address</label>' +
            '<input type="email" id="inq-email" name="email" required placeholder="your.email@example.com" autocomplete="email"></div>' +
            '<div class="form-group"><label for="inq-msg">Message <span style="text-transform:none;font-weight:400;letter-spacing:0;opacity:0.7;">(optional)</span></label>' +
            '<textarea id="inq-msg" name="message" placeholder="Questions about the work, shipping, or arranging a viewing..."></textarea></div>' +
            '<button type="submit" class="btn solid" style="width:100%;">Send Inquiry</button>' +
            '<div class="form-status" role="status"></div>' +
            '<p class="consent">Your name, email and message are sent to the studio through Formspree and used only to answer you. ' +
            'See the <a href="/privacy/">Privacy Policy</a>.</p>' +
            '<p class="direct-line">Prefer email? Write directly to ' +
            '<a href="mailto:ba.adamsson@gmail.com?subject=Inquiry: ' + encodeURIComponent(art.title) + '">ba.adamsson@gmail.com</a></p>' +
            '</form>';
    }

    /* ---------- routing ---------- */

    var VIEWS = ['home', 'about', 'work'];

    function showView(name) {
        VIEWS.forEach(function (v) {
            var el = byId('view-' + v);
            if (el) el.classList.toggle('active', v === name);
        });
    }

    function setNav(route) {
        [].forEach.call(document.querySelectorAll('nav.main a'), function (a) {
            var on = a.dataset.route === route;
            a.classList.toggle('active', on);
            if (on) a.setAttribute('aria-current', 'page');
            else a.removeAttribute('aria-current');
        });
    }

    function setMeta(title, path) {
        document.title = title;
        var c = document.querySelector('link[rel=canonical]');
        if (c) c.setAttribute('href', 'https://www.boakeadamsson.com' + path);
    }

    /* Returns false when the path is not one this script handles, so the
       browser can follow the link normally: the about page, the legal pages,
       admin, anything new. The about page is a leaf destination rather than a
       browsing surface, so it is served as a real document instead of being
       inlined into all 69 other pages just to save one short navigation. */
    function render(path, push, restoreScroll) {
        var work = path.match(/^\/work\/([a-z0-9-]+)\/?$/);
        if (work) {
            if (!renderWork(work[1])) return false;
            var art = bySlug[work[1]];
            showView('work');
            setNav(null);
            setMeta(art.title + ' | Bo Åke Adamsson', '/work/' + art.slug + '/');
        } else {
            var filter = null;
            Object.keys(FILTER_PATH).forEach(function (k) {
                if (FILTER_PATH[k] === path) filter = k;
            });
            if (!filter) return false;
            renderGallery(filter);
            showView('home');
            setNav(filter === 'all' ? 'gallery' : filter);
            setMeta(filter === 'all'
                ? 'Bo Åke Adamsson, Swedish Painter & Sculptor | Originals, Bronzes, Lithographs'
                : FILTER_TITLES[filter] + ' | Bo Åke Adamsson', path);
        }

        if (push) history.pushState({ path: path }, '', path);
        if (!restoreScroll) window.scrollTo(0, 0);
        watchReveals();
        return true;
    }

    /* Older shared links used #work/13, #about, #oil. Keep them working. */
    function legacyHashPath() {
        var h = location.hash.replace(/^#/, '');
        if (!h) return null;
        var m = h.match(/^work\/(\d+)$/);
        if (m) {
            var art = DATA.filter(function (a) { return a.id === parseInt(m[1], 10); })[0];
            return art ? '/work/' + art.slug + '/' : '/';
        }
        if (h === 'gallery') return '/';
        if (h === 'about') return '/about/';
        if (FILTER_PATH[h]) return FILTER_PATH[h];
        return null;
    }

    document.addEventListener('click', function (e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        var a = e.target.closest ? e.target.closest('a') : null;
        if (!a || a.target || a.hasAttribute('download')) return;
        if (a.origin && a.origin !== location.origin) return;
        if (a.getAttribute('href') && a.getAttribute('href').charAt(0) === '#') return;
        if (render(a.pathname, true)) e.preventDefault();
    });

    window.addEventListener('popstate', function () {
        if (!render(location.pathname, false, true)) location.reload();
    });

    /* ---------- forms ---------- */

    var ENDPOINTS = {
        inquiry: 'https://formspree.io/f/xlgjvpkk',
        newsletter: 'https://formspree.io/f/xwvlzyvr'
    };

    async function post(form, endpoint, extra) {
        var btn = form.querySelector('button[type=submit]');
        var status = form.querySelector('.form-status');
        var label = btn.innerText;
        btn.innerText = 'Sending...';
        btn.disabled = true;
        status.className = 'form-status';

        var body = new FormData(form);
        if (extra) Object.keys(extra).forEach(function (k) { body.append(k, extra[k]); });

        try {
            var res = await fetch(endpoint, {
                method: 'POST',
                body: body,
                headers: { Accept: 'application/json' }
            });
            if (!res.ok) throw new Error('bad status');
            form.reset();
            btn.innerText = label === 'Subscribe' ? 'Subscribed' : 'Inquiry Sent';
            status.className = 'form-status ok';
            status.textContent = label === 'Subscribe'
                ? 'Thank you, you are on the list.'
                : 'Thank you. Your message is with the studio and you will hear back personally.';
        } catch (err) {
            btn.innerText = label;
            btn.disabled = false;
            status.className = 'form-status err';
            status.innerHTML = 'Something went wrong. Please email ' +
                '<a href="mailto:ba.adamsson@gmail.com">ba.adamsson@gmail.com</a> directly.';
        }
    }

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form.matches('.inquiry-form')) {
            e.preventDefault();
            post(form, ENDPOINTS.inquiry, { Artwork_Title: form.dataset.inquiry });
        } else if (form.matches('.newsletter-form')) {
            e.preventDefault();
            post(form, ENDPOINTS.newsletter);
        }
    });

    /* ---------- boot ---------- */

    watchImages();
    watchReveals();

    var legacy = legacyHashPath();
    if (legacy) {
        if (render(legacy, false)) {
            history.replaceState({ path: legacy }, '', legacy);
        } else {
            // A route this script does not render, e.g. #about -> /about/.
            location.replace(legacy);
        }
    } else {
        // The page arrived fully rendered; just mark the state as ours so
        // popstate knows it can handle the way back.
        history.replaceState({ path: location.pathname }, '', location.pathname);
        var w = location.pathname.match(/^\/work\/([a-z0-9-]+)\/?$/);
        if (w && bySlug[w[1]]) renderWork(w[1]);
    }
})();
