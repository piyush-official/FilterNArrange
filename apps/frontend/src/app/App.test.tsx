// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the running banner", () => {
    render(<App />);
    expect(screen.getByText("FilterNArrange — running")).toBeInTheDocument();
  });
});
