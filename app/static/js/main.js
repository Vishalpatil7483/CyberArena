/* CyberArena base scripts */

// Collapse the mobile navbar after tapping a nav link.
document.addEventListener("DOMContentLoaded", () => {
    const navbarCollapse = document.getElementById("mainNavbar");
    if (!navbarCollapse) return;

    navbarCollapse.querySelectorAll(".nav-link").forEach((link) => {
        link.addEventListener("click", () => {
            const collapse = bootstrap.Collapse.getInstance(navbarCollapse);
            if (collapse && navbarCollapse.classList.contains("show")) {
                collapse.hide();
            }
        });
    });
});
