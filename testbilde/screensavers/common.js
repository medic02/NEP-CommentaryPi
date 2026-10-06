// Shared helpers for nep-no-screensaver
;(function () {
  // ── Transparent mode ──────────────────────────────────

  const params = new URLSearchParams(window.location.search)
  window.isTransparent = params.get('transparent') === 'true'

  if (window.isTransparent) {
    document.documentElement.style.background = 'transparent'
    document.body.style.background = 'transparent'
    const canvas = document.querySelector('canvas')
    if (canvas) canvas.style.background = 'transparent'
  }

  // ── Utilities ─────────────────────────────────────────

  window.wobble = function (min, max) {
    return min + Math.random() * (max - min)
  }

  window.resizeCanvas = function (canvas, ctx, dpr, W, H) {
    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
})()
