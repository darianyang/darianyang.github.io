/*
	Theme toggle (dark / light mode)
	- Defaults to the OS / browser preference (prefers-color-scheme)
	- Persists the user's manual choice in localStorage
*/

(function () {

	// ---------- helpers ----------

	function getPreferred() {
		var saved = localStorage.getItem('theme');
		if (saved) return saved;           // user has a saved preference
		if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
			return 'dark';
		return 'light';
	}

	function apply(theme) {
		document.documentElement.setAttribute('data-theme', theme);

		var icon = document.querySelector('#theme-toggle .theme-icon');
		if (icon) {
			// show sun when dark (clicking will switch to light), moon when light
			icon.className = theme === 'dark'
				? 'theme-icon fa fa-sun-o'
				: 'theme-icon fa fa-moon-o';
		}
	}

	// ---------- apply immediately to avoid FOUC ----------

	apply(getPreferred());

	// ---------- watch for OS-level changes ----------

	if (window.matchMedia) {
		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
			// only follow system if the user hasn't made a manual choice
			if (!localStorage.getItem('theme')) {
				apply(e.matches ? 'dark' : 'light');
			}
		});
	}

	// ---------- wire up the toggle button after DOM is ready ----------

	document.addEventListener('DOMContentLoaded', function () {
		var btn = document.getElementById('theme-toggle');
		if (!btn) return;

		// Make sure the icon reflects the current state
		apply(document.documentElement.getAttribute('data-theme') || 'light');

		btn.addEventListener('click', function () {
			var current = document.documentElement.getAttribute('data-theme') || 'light';
			var next    = current === 'dark' ? 'light' : 'dark';
			apply(next);
			localStorage.setItem('theme', next);
		});
	});

})();
