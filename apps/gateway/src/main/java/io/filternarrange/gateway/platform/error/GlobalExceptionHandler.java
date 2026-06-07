// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.error;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorEnvelope> validation(MethodArgumentNotValidException ex) {
        String msg = ex.getBindingResult().getFieldErrors().stream()
            .map(f -> f.getField() + ": " + f.getDefaultMessage())
            .collect(Collectors.joining("; "));
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ErrorEnvelope.of("VALIDATION_FAILED", msg, TraceIdFilter.current()));
    }

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ErrorEnvelope> app(AppException ex) {
        return ResponseEntity.status(ex.httpStatus())
            .body(ErrorEnvelope.of(ex.code(), ex.getMessage(), TraceIdFilter.current()));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<ErrorEnvelope> illegalState(IllegalStateException ex) {
        String m = ex.getMessage();
        return switch (m) {
            case "EMAIL_TAKEN" -> ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ErrorEnvelope.of("EMAIL_TAKEN", "Email already registered", TraceIdFilter.current()));
            case "BAD_CREDS" -> ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ErrorEnvelope.of("BAD_CREDS", "Invalid credentials", TraceIdFilter.current()));
            case "NO_USER" -> ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ErrorEnvelope.of("NO_USER", "User not found", TraceIdFilter.current()));
            default -> ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorEnvelope.of("INTERNAL", m, TraceIdFilter.current()));
        };
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorEnvelope> fallback(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorEnvelope.of("INTERNAL", ex.getMessage(), TraceIdFilter.current()));
    }
}
