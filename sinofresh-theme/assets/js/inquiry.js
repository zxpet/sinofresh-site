/*
 * SINO FRESH — the inquiry dialog on a formula detail page (batch H4).
 *
 * Two jobs, both of them about the same widget: reveal the capsule in the
 * float stack once the visitor has reached the parameter band, and drive the
 * dialog the capsule opens.
 *
 * Reveal: the capsule is emitted with `hidden` (sinofresh_inquiry_button()
 * sets it in the markup, not in CSS) and this file removes it when the
 * parameter band's top has crossed the middle of the viewport — the brief's
 * "after scrolling to the parameter band". One-way: once shown it stays, so
 * a visitor who scrolls back up does not watch the CTA disappear. If the
 * band is missing (a record whose meta proves nothing renders no band) the
 * capsule is shown immediately, because the trigger is about the page, not
 * the band.
 *
 * Dialog: same interaction language as the certificate dialog — `hidden`
 * plus `is-open` with one frame between them so the fade and the rise both
 * play, a body lock class, Escape and the backdrop close it, and focus
 * returns to the opener. Reused deliberately: three dialogs on one site that
 * close differently are three bugs waiting to be filed.
 *
 * Submit: fetch POST to the endpoint, JSON in, JSON out. The values the
 * server cannot re-derive — name, email, company, country, message — are the
 * only ones sent; the selection panel is rebuilt server-side from the post
 * id, so the posted body carries no claim about the product. Success swaps
 * the form for the confirmation and closes after three seconds; a failure
 * keeps the form, prints the endpoint's message and re-stamps the clock,
 * because a visitor who had to read an error needs more than three seconds.
 */
(function () {
	'use strict';

	/* The dialog markup is printed on wp_footer, next to this script, and a
	   classic footer script executes while the parser is still going: whether
	   the dialog exists yet depends on the two hook priorities, and getting
	   that wrong is silent — no error, no dialog, a capsule that never shows.
	   Wait for the parser to finish rather than assume an order. */
	function init() {
		var btn   = document.querySelector('[data-sf-inquiry-open]');
		/* One element is both the backdrop and the centring box (see style.css), so
		   "clicked outside the panel" is "the event target is the backdrop". */
		var modal = document.querySelector('.sf-inquiry-modal');
		if (!btn || !modal) {
			return;
		}

		var form     = modal.querySelector('.sf-inquiry-form');
		var status   = modal.querySelector('.sf-inquiry-form__status');
		var success  = modal.querySelector('.sf-inquiry-modal__success');
		var closeBtn = modal.querySelector('.sf-inquiry-modal__close');
		var stamp    = form ? form.querySelector('input[name="ts"]') : null;
		var opener   = null;
		var timer    = null;

		var LOCK  = 'sf-inquiry-lock';
		var SLOPE = 0.5;           /* fraction of the viewport the band must cross  */

		/* ---------------------------------------------------------------- reveal */

		var band    = document.querySelector('.sf-fdetail2__params');
		var revealed = false;
		var ticking  = false;

		function reveal() {
			revealed = true;
			btn.hidden = false;
			btn.classList.add('is-visible');
			window.removeEventListener('scroll', onScroll);
			window.removeEventListener('resize', onScroll);
		}

		function onScroll() {
			if (ticking) {
				return;
			}
			ticking = true;
			window.requestAnimationFrame(function () {
				ticking = false;
				if (revealed) {
					return;
				}
				if (band.getBoundingClientRect().top <= window.innerHeight * SLOPE) {
					reveal();
				}
			});
		}

		if (!band) {
			reveal();
		} else {
			window.addEventListener('scroll', onScroll, { passive: true });
			window.addEventListener('resize', onScroll);
			onScroll();          /* a deep link that lands past the band on load */
		}

		/* ----------------------------------------------------------------- dialog */

		function open() {
			if (!modal.hidden) {
				return;
			}
			opener = btn;
			modal.hidden = false;
			document.body.classList.add(LOCK);
			if (stamp) {
				stamp.value = String(Date.now());
			}
			/* One frame between "displayed" and "is-open" or the transition has
			   no start value to animate from — the same reason cert-modal.js
			   splits them. */
			window.requestAnimationFrame(function () {
				modal.classList.add('is-open');
				var first = form && !form.hidden
					? form.querySelector('input[name="name"]')
					: closeBtn;
				if (first) {
					first.focus({ preventScroll: true });
				}
			});
		}

		function close() {
			if (modal.hidden) {
				return;
			}
			if (timer) {
				window.clearTimeout(timer);
				timer = null;
			}
			modal.classList.remove('is-open');
			modal.hidden = true;
			document.body.classList.remove(LOCK);
			if (opener) {
				opener.focus({ preventScroll: true });
			}
		}

		btn.addEventListener('click', function (event) {
			/* The href is /contact/#quote so the markup works without this file;
			   with it, the click belongs to the dialog. */
			event.preventDefault();
			open();
		});
		if (closeBtn) {
			closeBtn.addEventListener('click', close);
		}
		/* The backdrop is the dialog's own outer box: a click that lands on it and
		   not on the panel closes. On a phone the panel fills it, so this only
		   ever fires on desktop — no breakpoint test needed. */
		modal.addEventListener('click', function (event) {
			if (event.target === modal) {
				close();
			}
		});
		document.addEventListener('keydown', function (event) {
			if (!modal.hidden && event.key === 'Escape') {
				close();
			}
		});

		/* ----------------------------------------------------------------- submit */

		if (!form) {
			return;
		}

		function say(text) {
			if (status) {
				status.textContent = text;
			}
		}

		function payload() {
			var data = new FormData(form);
			function val(key) {
				var v = data.get(key);
				return typeof v === 'string' ? v.trim() : '';
			}
			return {
				name:    val('name'),
				email:   val('email'),
				company: val('company'),
				country: val('country'),
				message: val('message'),
				website: val('website'),
				formula: val('formula'),
				ts:      val('ts'),
				source:  window.location.href
			};
		}

		form.addEventListener('submit', function (event) {
			event.preventDefault();
			var body = payload();

			/* The server validates all of this again; doing it here too is only
			   so the visitor is not made to wait for a round trip to be told
			   their name is missing. */
			if (body.name === '') {
				say('Please tell us your name.');
				return;
			}
			if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(body.email)) {
				say('Please enter a valid email address.');
				return;
			}

			var submit = form.querySelector('.sf-inquiry-form__submit');
			if (submit) {
				submit.disabled = true;
			}
			say('Sending…');

			window.fetch('/wp-json/sinofresh/v1/inquiry', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			}).then(function (response) {
				return response.json().then(function (json) {
					return { ok: response.ok, json: json };
				});
			}).then(function (result) {
				if (!result.ok) {
					throw new Error(result.json && result.json.message
						? result.json.message
						: 'We could not send that just now.');
				}
				form.hidden = true;
				if (success) {
					success.hidden = false;
				}
				say('');
				timer = window.setTimeout(close, 3000);
			}).catch(function (error) {
				/* Re-stamp: the three-second floor is about how long the form was
				   on screen, and a failed attempt followed by an immediate retry
				   must not be mistaken for a machine. */
				if (stamp) {
					stamp.value = String(Date.now());
				}
				say(error && error.message ? error.message : 'We could not send that just now.');
			}).then(function () {
				if (submit) {
					submit.disabled = false;
				}
			});
		});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
