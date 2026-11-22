// Run before styles so a new page paints in the last confirmed theme.
try {
  if (localStorage.getItem("memory-interface-theme") === "neon") {
    document.documentElement.dataset.theme = "neon";
    document.querySelector('meta[name="theme-color"]').content = "#141715";
  }
} catch {
  // The authenticated appearance endpoint still works with storage disabled.
}
