(function () {
  const initMermaid = () => {
    const mermaid = window.mermaid;
    if (!mermaid) {
      return;
    }

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "default",
    });
  };

  const renderMermaid = () => {
    const mermaid = window.mermaid;
    if (!mermaid) {
      return;
    }

    mermaid.init(undefined, document.querySelectorAll(".language-mermaid, .mermaid"));
  };

  initMermaid();

  if (window.document$ && window.document$.subscribe) {
    window.document$.subscribe(renderMermaid);
  } else {
    document.addEventListener("DOMContentLoaded", renderMermaid);
  }
})();
