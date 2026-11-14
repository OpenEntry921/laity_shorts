const players = [...document.querySelectorAll('.player')].map((element) => ({
  video: element.querySelector('video'),
  play: element.querySelector('.play'),
  failure: element.querySelector('.failure'),
  retry: element.querySelector('.retry'),
  attempt: 0,
}));

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
