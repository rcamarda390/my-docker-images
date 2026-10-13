package server

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// Generate oversized input without allocating it in the test client.
type xrayBody struct{ read int64 }

func (b *xrayBody) Read(p []byte) (int, error) {
	const size int64 = (100 << 20) + 65536
	if b.read >= size {
		return 0, io.EOF
	}
	if int64(len(p)) > size-b.read {
		p = p[:size-b.read]
	}
	for i := range p {
		p[i] = ' '
	}
	b.read += int64(len(p))
	return len(p), nil
}

func TestXrayBodyLimit(t *testing.T) {
	const limit int64 = 100 << 20
	s := NewStreamableHTTPServer(NewMCPServer("body-limit-test", "1"))
	for _, length := range []int64{limit + 1, -1} {
		body := &xrayBody{}
		r := httptest.NewRequest(http.MethodPost, "http://localhost/mcp", nil)
		r.Body = io.NopCloser(body)
		r.ContentLength = length
		r.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		s.ServeHTTP(w, r)
		if w.Code != http.StatusRequestEntityTooLarge {
			t.Fatalf("length %d: got HTTP %d, want 413", length, w.Code)
		}
		if length > limit && body.read != 0 {
			t.Fatal("known oversized body was read")
		}
		if body.read > limit+1 {
			t.Fatalf("read %d bytes, limit is %d plus one probe byte", body.read, limit)
		}
	}
	r := httptest.NewRequest(http.MethodPost, "http://localhost/mcp", strings.NewReader(
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Accept", "application/json, text/event-stream")
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "protocolVersion") {
		t.Fatalf("normal initialization failed: HTTP %d: %s", w.Code, w.Body.String())
	}
}
