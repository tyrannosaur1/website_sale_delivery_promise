/* Delivery promise countdown.
 *
 * The page renders the sentence once, with the seconds left at render time and
 * the absolute cut-off instant. A tab left open would otherwise keep showing a
 * deadline that has already expired, so this script reprints the countdown
 * every second and swaps in the "Order now" wording at zero.
 *
 * The deadline is never read from the visitor's clock: it is the server's
 * value, shaved by the time elapsed since this script started (a monotonic
 * reading), so a wrong system clock cannot extend the promise and only real
 * time passing can end it.
 */
(function () {
    'use strict';

    // Mirrors format_countdown_seconds() in models/estimate.py.
    function formatRemaining(totalSeconds) {
        var minutes = Math.floor(Math.max(Math.floor(totalSeconds), 0) / 60);
        if (minutes >= 60) {
            var rest = minutes % 60;
            return Math.floor(minutes / 60) + 'h ' + (rest < 10 ? '0' + rest : rest) + 'm';
        }
        return minutes + 'm';
    }

    function monotonicNow() {
        if (window.performance && window.performance.now) {
            return window.performance.now();
        }
        return new Date().getTime();
    }

    function startCountdown(node) {
        var total = parseInt(node.getAttribute('data-dps-seconds'), 10);
        var sentence = node.querySelector('.o_dps_sentence');
        var counter = node.querySelector('.o_dps_countdown');
        if (!sentence || !counter || isNaN(total)) {
            return;
        }
        var expired = node.getAttribute('data-dps-expired') || '';
        var startedAt = monotonicNow();
        var timer = null;

        function stop() {
            if (timer !== null) {
                window.clearInterval(timer);
                timer = null;
            }
            // The element is no longer a live countdown: drop the hooks so a
            // later pass over the page cannot start a second timer on it.
            node.removeAttribute('data-dps-seconds');
            node.removeAttribute('data-dps-cutoff');
            node.removeAttribute('data-dps-expired');
        }

        function tick() {
            var left = total - Math.floor((monotonicNow() - startedAt) / 1000);
            if (left <= 0) {
                sentence.textContent = expired;
                if (counter.parentNode) {
                    counter.parentNode.removeChild(counter);
                }
                stop();
                return;
            }
            counter.textContent = formatRemaining(left);
        }

        timer = window.setInterval(tick, 1000);
    }

    function init() {
        var nodes = document.querySelectorAll('[data-dps-seconds]');
        for (var i = 0; i < nodes.length; i++) {
            startCountdown(nodes[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
