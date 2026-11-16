// Run in the head so the feed stays hidden during initial positioning.
// Server-rendered pages already start with the requested reel for no-JS users.
document.documentElement.classList.add('js');
history.scrollRestoration = 'manual';

function initReels() {
  const feed = document.getElementById('feed');
  if (!feed) return;
  const clips = [...feed.querySelectorAll('.clip')].sort((a, b) => Number(a.dataset.order) - Number(b.dataset.order));
  const counter = document.querySelector('.reel-count');
  const hint = document.querySelector('.swipe-hint');
  if (!clips.length) { feed.dataset.ready = 'true'; return; }
  const multiple = clips.length > 1;
  let activeClip = null;
  let hintDismissed = false;
  const players = clips.map((clip) => {
    const element = clip.querySelector('.player');
    return {
    clip,
    video: element.querySelector('video'),
    play: element.querySelector('.play'),
    failure: element.querySelector('.failure'),
    retry: element.querySelector('.retry'),
    attempt: 0,
    };
  });

  function showFailure(player) {
    player.play.hidden = true;
    player.failure.hidden = false;
    player.video.controls = false;
  }

  function pauseOthers(active) {
    for (const player of players) {
      if (player !== active) {
        player.attempt += 1;
        player.video.pause();
      }
    }
  }

  async function start(player, retry = false) {
    activate(player.clip);
    if (hint) hint.hidden = true;
    hintDismissed = true;
    const attempt = ++player.attempt;
    pauseOthers(player);
    player.failure.hidden = true;
    player.video.controls = true;
    player.play.hidden = true;
    if (retry) player.video.load();
    player.video.focus({ preventScroll: true });
    try {
      await player.video.play();
    } catch (error) {
      if (attempt !== player.attempt) return;
      if (error.name === 'AbortError') {
        player.play.hidden = false;
      } else {
        showFailure(player);
      }
    }
  }

  for (const player of players) {
    // Native controls stay in the HTML for browsers with JavaScript disabled.
    player.video.controls = false;
    player.play.hidden = false;
    player.play.addEventListener('click', () => start(player));
    player.retry.addEventListener('click', () => start(player, true));
    player.video.addEventListener('play', () => {
      if (player.video.paused) return;
      if (player.clip !== activeClip) { player.video.pause(); return; }
      if (hint) hint.hidden = true;
      hintDismissed = true;
      pauseOthers(player);
      player.play.hidden = true;
      player.failure.hidden = true;
      player.video.controls = true;
    });
    player.video.addEventListener('pause', () => {
      if (player.video.paused && !player.video.error && player.failure.hidden) player.play.hidden = false;
    });
    player.video.addEventListener('ended', () => { player.play.hidden = false; });
    player.video.addEventListener('error', () => showFailure(player));
    player.video.querySelector('source').addEventListener('error', () => showFailure(player));
  }

  function activate(clip) {
    if (clip === activeClip) return;
    if (activeClip) hintDismissed = true;
    activeClip = clip;
    const index = clips.indexOf(clip);
    if (counter) counter.textContent = (index + 1) + ' / ' + clips.length;
    if (hint) hint.hidden = hintDismissed || index !== 0;
    for (const player of players) {
      const selected = player.clip === clip;
      player.video.tabIndex = selected ? 0 : -1;
      player.play.tabIndex = selected ? 0 : -1;
      player.retry.tabIndex = selected ? 0 : -1;
      if (!selected) {
        player.attempt += 1;
        player.video.pause();
      }
    }
    // Keep the base page as / when scrolling; a copied address must not silently
    // switch the reader into single-video mode on refresh.
  }

  function nearestClip() {
    const center = feed.scrollTop + feed.clientHeight / 2;
    return clips.reduce((nearest, clip) =>
      Math.abs(clip.offsetTop + clip.offsetHeight / 2 - center) <
      Math.abs(nearest.offsetTop + nearest.offsetHeight / 2 - center) ? clip : nearest);
  }

  const initial = clips[0];
  feed.scrollTop = 0;
  activate(initial);
  feed.dataset.ready = 'true';
  if (!multiple) return;

  let scrollFrame = 0;
  feed.addEventListener('scroll', () => {
    if (scrollFrame) return;
    scrollFrame = requestAnimationFrame(() => {
      scrollFrame = 0;
      activate(nearestClip());
    });
  }, { passive: true });
  window.addEventListener('pageshow', event => { if (event.persisted) activate(nearestClip()); });

}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initReels, { once: true });
} else {
  initReels();
}
