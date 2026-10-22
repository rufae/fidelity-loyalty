import { describe, expect, it } from "vitest";

import { reviewBlockReason, signupBlockReason } from "../components/nfc-view";
import type { Program, ReviewDestination } from "../lib/fidelity";

const PROGRAM: Program = {
  id: "p1",
  merchant_id: "m1",
  name: "Club",
  slug: "club",
  program_type: "stamps",
  description: null,
  terms: null,
  terms_version: 1,
  status: "active",
  created_at: "2026-10-13T00:00:00Z",
  updated_at: "2026-10-13T00:00:00Z",
  published_at: null,
};

const destination = (status: string): ReviewDestination => ({
  id: "d1",
  provider: "google",
  review_url: "https://g.page/r/ejemplo/review",
  verification_status: status,
  verified_at: status === "verified" ? "2026-10-13T00:00:00Z" : null,
  updated_at: "2026-10-13T00:00:00Z",
});

describe("bloqueos del formulario de etiquetas (regresión del 422 real)", () => {
  it("impide la etiqueta de alta sin programa y explica qué hacer", () => {
    expect(signupBlockReason([])).toMatch(/Programas/);
  });

  it("permite la etiqueta de alta cuando hay al menos un programa", () => {
    expect(signupBlockReason([PROGRAM])).toBeNull();
  });

  it("impide la etiqueta de reseñas sin enlace guardado", () => {
    expect(reviewBlockReason(null)).toMatch(/Reseñas Google/);
  });

  it("impide la etiqueta de reseñas si el enlace está sin verificar", () => {
    expect(reviewBlockReason(destination("unverified"))).toMatch(/verificar/);
  });

  it("permite la etiqueta de reseñas con enlace verificado", () => {
    expect(reviewBlockReason(destination("verified"))).toBeNull();
  });
});
