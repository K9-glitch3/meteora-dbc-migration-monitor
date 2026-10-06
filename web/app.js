"use strict";

fetch("../evidence/stream_vs_chain_20261001.json")
  .then((response) => {
    if (!response.ok) throw new Error("Evidence unavailable");
    return response.json();
  })
  .then((data) => {
    const values = [
      data.sampled,
      data.A_stream_equals_chain,
      data.B_math_equals_chain,
      data.B_not_applicable + data.B_unsupported_pool + data.B_partial_fill_skipped,
    ];
    document.querySelectorAll("#metrics dd").forEach((node, index) => {
      node.textContent = String(values[index]);
    });
  })
  .catch(() => {
    // The checked-in values remain visible when opened from a browser that blocks file fetches.
  });
