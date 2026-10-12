import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import { fieldErrorsOf, messageOf } from "./errors";

const validation = new ApiError(422, "validation_error", "Request validation failed.", [
  { field: "password", message: "Value error, Password must mix letters and numbers" },
  { field: "email", message: "value is not a valid email address" },
]);

describe("messageOf", () => {
  it("shows the first validation message without the pydantic prefix", () => {
    expect(messageOf(validation)).toBe("Password must mix letters and numbers");
  });

  it("uses the server message for other API errors", () => {
    expect(messageOf(new ApiError(401, "unauthorized", "Invalid email or password."))).toBe("Invalid email or password.");
  });

  it("falls back to a generic message for unknown errors", () => {
    expect(messageOf(new Error("boom"))).toBe("Something went wrong. Please try again.");
    expect(messageOf("oops")).toBe("Something went wrong. Please try again.");
  });
});

describe("fieldErrorsOf", () => {
  it("maps details to fields, keeping the first message per field", () => {
    expect(fieldErrorsOf(validation)).toEqual({
      password: "Password must mix letters and numbers",
      email: "value is not a valid email address",
    });
  });

  it("returns nothing for non-validation errors", () => {
    expect(fieldErrorsOf(new Error("x"))).toEqual({});
    expect(fieldErrorsOf(new ApiError(500, "http_error", "Failed"))).toEqual({});
  });
});
