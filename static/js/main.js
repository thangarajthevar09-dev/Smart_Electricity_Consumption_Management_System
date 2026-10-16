document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((item) => {
    window.setTimeout(() => {
      if (item.isConnected) item.classList.add("flash-fade");
      window.setTimeout(() => { if (item.isConnected) item.remove(); }, 350);
    }, 6500);
  });
});
