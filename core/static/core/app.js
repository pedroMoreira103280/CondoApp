/* CondoApp — pequenos comportamentos da interface, sem framework. */
(function () {
  "use strict";

  // ---------- Copiar link de convite ----------
  document.querySelectorAll("[data-copiar]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.getElementById(botao.dataset.copiar);
      campo.select();
      var feito = function () {
        var texto = botao.textContent;
        botao.textContent = "Copiado!";
        setTimeout(function () { botao.textContent = texto; }, 1800);
      };
      if (navigator.clipboard) navigator.clipboard.writeText(campo.value).then(feito, function () { document.execCommand("copy"); feito(); });
      else { document.execCommand("copy"); feito(); }
    });
  });

  // ---------- QR Code do convite (biblioteca qrcode-generator, carregada só nessas páginas) ----------
  window.CondoApp = {
    desenharQRCodes: function () {
      if (typeof window.qrcode !== "function") return; // sem internet: fica a mensagem com o link
      document.querySelectorAll("[data-qrcode]").forEach(function (caixa) {
        var qr = window.qrcode(0, "M");
        qr.addData(caixa.dataset.qrcode);
        qr.make();
        caixa.innerHTML = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
        caixa.classList.add("qrcode-pronto");
      });
    }
  };

  // ---------- Abrir chamado ----------
  var tipo = document.getElementById("id_tipo");
  var privado = document.getElementById("id_privado");
  var parecidos = document.querySelectorAll("[data-parecido]");
  var caixaParecidos = document.getElementById("parecidos");
  var privadoTocado = false;
  if (privado) privado.addEventListener("change", function () { privadoTocado = true; });

  function atualizarChamado(evento) {
    if (!tipo) return;
    // Convivência é privada por padrão, para não expor quem reclama.
    if (evento && privado && !privadoTocado) privado.checked = tipo.value === "barulho";
    // Mostra chamados abertos do mesmo tipo: "também estou afetado" em vez de duplicar.
    if (caixaParecidos) {
      var total = 0;
      parecidos.forEach(function (item) {
        var mostra = tipo.value && item.dataset.parecido === tipo.value;
        item.hidden = !mostra;
        if (mostra) total++;
      });
      caixaParecidos.hidden = total === 0;
    }
  }
  if (tipo) {
    tipo.addEventListener("change", atualizarChamado);
    atualizarChamado();
  }

  // ---------- Imprimir ----------
  document.querySelectorAll("[data-imprimir]").forEach(function (botao) {
    botao.addEventListener("click", function () { window.print(); });
  });
})();
