setInterval(() => {
    for (let loading of document.querySelectorAll("div[loading]")) {
        loading.removeAttribute("loading");
        loading.classList.add("loading");
        for (let i = 0; i < 3; i++) {
            loading.appendChild(document.createElement("div"));
        }
    }
});
