// Plain JavaScript, no framework. The only auth logic here is: attach the token to /api/
// requests, and show the login form after a 401. The token is never decoded.
(function () {
  "use strict";

  var API_BASE = ((window.APP_CONFIG && window.APP_CONFIG.apiBaseUrl) || "").replace(/\/+$/, "");
  var TOKEN_KEY = "access_token";
  var $ = function (id) { return document.getElementById(id); };

  // ---- small helpers -------------------------------------------------------------------

  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (key) { node[key] = props[key]; });
    (children || []).forEach(function (child) {
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function getToken() {
    try { return sessionStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }
  function setToken(token) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token); else sessionStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* storage unavailable: the token only lives for this page view */ memoryToken = token; }
  }
  var memoryToken = null;
  function currentToken() { return getToken() || memoryToken; }

  function setStatus(node, text, kind) {
    node.textContent = text || "";
    node.className = "status" + (kind ? " " + kind : "");
  }

  // ---- API calls + debug panel ---------------------------------------------------------

  // Resolves to {status, ok, data, text, unreachable}; never rejects.
  async function api(method, path, body) {
    var url = API_BASE + path;
    var headers = {};
    if (body !== undefined) headers["content-type"] = "application/json";
    if (path.indexOf("/api/") === 0 && currentToken()) {
      headers["authorization"] = "Bearer " + currentToken();   // only ever sent to /api/...
    }
    var started = performance.now();
    var result = { status: 0, ok: false, data: null, text: "", unreachable: false, headers: {} };
    try {
      var response = await fetch(url, {
        method: method,
        headers: headers,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
      result.status = response.status;
      result.ok = response.ok;
      response.headers.forEach(function (value, name) { result.headers[name] = value; });
      result.text = await response.text();
      // 401/429 from the gateway are often plain text, so only parse what says it is JSON.
      if ((response.headers.get("content-type") || "").indexOf("json") !== -1) {
        try { result.data = JSON.parse(result.text); } catch (e) { result.data = null; }
      }
      // A 404 produced by the frontend's own nginx means no gateway is routing the path yet.
      if (response.status === 404 && result.headers["x-service-name"] === "frontend") {
        result.unreachable = true;
      }
    } catch (e) {
      result.unreachable = true;
      result.text = String(e);
    }
    showDebug(method, url, result, performance.now() - started);
    if (path.indexOf("/api/") === 0 && result.status === 401) setToken(null);
    return result;
  }

  function showDebug(method, url, result, ms) {
    var status = result.status ? String(result.status) : "no response";
    $("debug-summary").textContent = method + " " + url + " -> " + status + " in " + Math.round(ms) + " ms";
    var names = Object.keys(result.headers).sort();
    $("debug-headers").textContent = names.length
      ? names.map(function (n) { return n + ": " + result.headers[n]; }).join("\n")
      : "(none)";
    $("debug-body").textContent = result.text ? result.text.slice(0, 600) : "(empty)";
  }

  // The most useful short description of a failed response.
  function describeFailure(result) {
    if (result.unreachable) return "API not reachable";
    if (result.status === 429) return "Too many requests, try again in a moment.";
    if (result.data && result.data.message) return result.data.message;
    if (result.text) return result.text.slice(0, 200);
    return "Request failed with status " + result.status;
  }

  // ---- login / register form -----------------------------------------------------------

  var authForm = $("auth-form");
  var pendingRetry = null;
  var authHome = null;       // {slot, panelBody} where the form is currently shown

  function showAuth(slot, panelBody, retry) {
    hideAuth();
    pendingRetry = retry || null;
    authHome = { slot: slot, panelBody: panelBody };
    if (panelBody) panelBody.hidden = true;
    slot.appendChild(authForm);
    authForm.hidden = false;
    setStatus($("auth-status"), "");
    $("auth-email").focus();
  }

  function hideAuth() {
    if (!authHome) return;
    authForm.hidden = true;
    document.body.appendChild(authForm);
    if (authHome.panelBody) authHome.panelBody.hidden = false;
    authHome = null;
  }

  function updateSession() {
    var loggedIn = !!currentToken();
    $("session-state").textContent = loggedIn ? "Logged in" : "Not logged in";
    $("login-button").hidden = loggedIn;
    $("logout-button").hidden = !loggedIn;
  }

  async function submitAuth(register) {
    var status = $("auth-status");
    var creds = { email: $("auth-email").value, password: $("auth-password").value };
    setStatus(status, register ? "Registering..." : "Logging in...");
    if (register) {
      var created = await api("POST", "/auth/register", creds);
      if (!created.ok) { setStatus(status, describeFailure(created), "error"); return; }
    }
    var login = await api("POST", "/auth/login", creds);
    if (!login.ok || !login.data || !login.data.access_token) {
      setStatus(status, describeFailure(login), "error");   // no loop back into the form
      return;
    }
    setToken(login.data.access_token);
    $("auth-password").value = "";
    updateSession();
    var retry = pendingRetry;
    pendingRetry = null;
    hideAuth();
    if (retry) retry();
  }

  authForm.addEventListener("submit", function (event) {
    event.preventDefault();
    submitAuth(false);
  });
  $("auth-register").addEventListener("click", function () {
    if (authForm.reportValidity()) submitAuth(true);
  });
  $("auth-cancel").addEventListener("click", function () { pendingRetry = null; hideAuth(); });

  $("login-button").addEventListener("click", function () {
    showAuth($("auth-top"), null, function () { loadOrders(); });
  });
  $("logout-button").addEventListener("click", function () {
    setToken(null);
    memoryToken = null;
    updateSession();
    clear($("order-list"));
    $("orders-meta").hidden = true;
    setStatus($("orders-status"), "Logged out.");
  });

  // ---- blog ----------------------------------------------------------------------------

  async function loadPosts() {
    var status = $("blog-status");
    var list = $("post-list");
    setStatus(status, "Loading...");
    var result = await api("GET", "/blog/posts");
    clear(list);
    if (!result.ok || !result.data) { setStatus(status, describeFailure(result), "error"); return; }
    setStatus(status, "");
    result.data.posts.forEach(function (post) {
      var link = el("a", { href: "#post-" + post.id, textContent: post.title });
      link.addEventListener("click", function (event) { event.preventDefault(); loadPost(post.id); });
      list.appendChild(el("li", {}, [
        link,
        el("div", { className: "muted", textContent: post.author + " · " + post.published_at.slice(0, 10) }),
        el("div", { textContent: post.summary })
      ]));
    });
  }

  async function loadPost(id) {
    var detail = $("post-detail");
    var result = await api("GET", "/blog/posts/" + encodeURIComponent(id));
    detail.hidden = false;
    clear(detail);
    if (!result.ok || !result.data) {
      detail.appendChild(el("p", { className: "status error", textContent: describeFailure(result) }));
      return;
    }
    detail.appendChild(el("h3", { textContent: result.data.title }));
    detail.appendChild(el("p", { textContent: result.data.body }));
  }

  // ---- newsletter ----------------------------------------------------------------------

  $("unsubscribe-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var status = $("newsletter-status");
    setStatus(status, "Sending...");
    var result = await api("POST", "/unsubscribe", { email: $("unsubscribe-email").value });
    if (result.ok && result.data) setStatus(status, result.data.message, "ok");
    else setStatus(status, describeFailure(result), "error");
  });

  // ---- orders --------------------------------------------------------------------------

  function renderOrders(data) {
    var meta = $("orders-meta");
    clear(meta);
    var rows = [["user_id", data.user_id], ["user_email", data.user_email], ["version", data.version]];
    if (data.recommendations) rows.push(["recommendations", data.recommendations.join(", ") || "(none)"]);
    rows.forEach(function (row) {
      meta.appendChild(el("dt", { textContent: row[0] }));
      meta.appendChild(el("dd", { textContent: row[1] }));
    });
    meta.hidden = false;

    var list = $("order-list");
    clear(list);
    (data.orders || []).forEach(function (order) {
      var price = order.stock && order.stock.price;
      list.appendChild(el("li", {}, [
        el("strong", { textContent: order.id }),
        el("div", { textContent: order.quantity + " × " + order.sku + " · " + order.created_at }),
        el("div", {
          className: "muted",
          textContent: order.stock
            ? order.stock.in_stock + " in stock" + (price ? " · " + price.amount + " " + price.currency : "")
            : ""
        })
      ]));
    });
  }

  // Run an orders request; on 401 show the login form in place of the panel and retry after login.
  async function ordersRequest(method, path, body, onSuccess) {
    var status = $("orders-status");
    setStatus(status, "Loading...");
    var result = await api(method, path, body);
    if (result.status === 401 && !result.unreachable) {
      setStatus(status, "");
      showAuth($("auth-orders"), $("orders-panel").querySelector(".panel-body"), function () {
        ordersRequest(method, path, body, onSuccess);
      });
      updateSession();
      return;
    }
    if (!result.ok || !result.data) { setStatus(status, describeFailure(result), "error"); return; }
    setStatus(status, "");
    onSuccess(result.data);
  }

  function loadOrders() {
    return ordersRequest("GET", "/api/orders", undefined, renderOrders);
  }

  $("orders-refresh").addEventListener("click", loadOrders);
  $("order-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var body = { sku: $("order-sku").value, quantity: parseInt($("order-quantity").value, 10) };
    ordersRequest("POST", "/api/orders", body, function () { loadOrders(); });
  });

  // ---- start ---------------------------------------------------------------------------

  updateSession();
  loadPosts();
  loadOrders();
})();
