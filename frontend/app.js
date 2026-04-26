const API_BASE_URL = "http://ec2-44-202-191-41.compute-1.amazonaws.com";

function getCurrentPage() {
  return window.location.pathname.split("/").pop();
}

function saveUserSession(user) {
  sessionStorage.setItem("user", JSON.stringify(user));
}

function getUserSession() {
  const user = sessionStorage.getItem("user");
  return user ? JSON.parse(user) : null;
}

function clearUserSession() {
  sessionStorage.removeItem("user");
}

async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value.trim();
  const message = document.getElementById("loginMessage");
  message.textContent = "";

  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.message || "email or password is invalid";
      return;
    }

    saveUserSession({
      email: data.email,
      username: data.username
    });

    window.location.href = "main.html";
  } catch (error) {
    message.textContent = "Unable to connect to server.";
  }
}

async function handleRegister(event) {
  event.preventDefault();

  const email = document.getElementById("registerEmail").value.trim();
  const username = document.getElementById("registerUsername").value.trim();
  const password = document.getElementById("registerPassword").value.trim();
  const message = document.getElementById("registerMessage");
  message.textContent = "";

  try {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password })
    });

    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.message || "The email already exists";
      return;
    }

    window.location.href = "login.html";
  } catch (error) {
    message.textContent = "Unable to connect to server.";
  }
}

function renderSongCard(song, actionLabel, actionHandler) {
  const card = document.createElement("div");
  card.className = "song-card";

  card.innerHTML = `
    <img src="${song.image_url}" alt="${song.artist}">
    <div class="song-info">
      <p><strong>Title:</strong> ${song.title}</p>
      <p><strong>Artist:</strong> ${song.artist}</p>
      <p><strong>Album:</strong> ${song.album}</p>
      <p><strong>Year:</strong> ${song.year}</p>
    </div>
    <div class="song-actions">
      <button>${actionLabel}</button>
    </div>
  `;

  card.querySelector("button").addEventListener("click", () => actionHandler(song));
  return card;
}

async function loadSubscriptions() {
  const user = getUserSession();
  const subscriptionList = document.getElementById("subscriptionList");

  if (!user || !subscriptionList) return;

  try {
    const response = await fetch(`${API_BASE_URL}/subscriptions?email=${encodeURIComponent(user.email)}`);
    const data = await response.json();

    subscriptionList.innerHTML = "";

    if (!response.ok || !data.subscriptions || data.subscriptions.length === 0) {
      subscriptionList.classList.add("empty-box");
      subscriptionList.textContent = "No subscriptions yet.";
      return;
    }

    subscriptionList.classList.remove("empty-box");

    data.subscriptions.forEach(song => {
      const card = renderSongCard(song, "Remove", removeSubscription);
      subscriptionList.appendChild(card);
    });
  } catch (error) {
    subscriptionList.classList.add("empty-box");
    subscriptionList.textContent = "Unable to load subscriptions.";
  }
}

async function handleQuery(event) {
  event.preventDefault();

  const title = document.getElementById("title").value.trim();
  const year = document.getElementById("year").value.trim();
  const artist = document.getElementById("artist").value.trim();
  const album = document.getElementById("album").value.trim();

  const queryMessage = document.getElementById("queryMessage");
  const queryResults = document.getElementById("queryResults");

  queryMessage.textContent = "";
  queryResults.innerHTML = "";

  if (!title && !year && !artist && !album) {
    queryMessage.textContent = "Please enter at least one search field.";
    return;
  }

  const params = new URLSearchParams();
  if (title) params.append("title", title);
  if (year) params.append("year", year);
  if (artist) params.append("artist", artist);
  if (album) params.append("album", album);

  try {
    const response = await fetch(`${API_BASE_URL}/query?${params.toString()}`);
    const data = await response.json();

    if (!response.ok || !data.results || data.results.length === 0) {
      queryMessage.textContent = "No result is retrieved. Please query again";
      return;
    }

    data.results.forEach(song => {
      const card = renderSongCard(song, "Subscribe", subscribeSong);
      queryResults.appendChild(card);
    });
  } catch (error) {
    queryMessage.textContent = "Unable to query music.";
  }
}

async function subscribeSong(song) {
  const user = getUserSession();
  if (!user) return;

  try {
    await fetch(`${API_BASE_URL}/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: user.email,
        ...song
      })
    });

    loadSubscriptions();
  } catch (error) {
    alert("Unable to subscribe song.");
  }
}

async function removeSubscription(song) {
  const user = getUserSession();
  if (!user) return;

  try {
    await fetch(`${API_BASE_URL}/remove`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: user.email,
        title: song.title,
        artist: song.artist
      })
    });

    loadSubscriptions();
  } catch (error) {
    alert("Unable to remove subscription.");
  }
}

function setupMainPage() {
  const user = getUserSession();

  if (!user) {
    window.location.href = "login.html";
    return;
  }

  const userName = document.getElementById("userName");
  const userAreaName = document.getElementById("userAreaName");
  const userAreaEmail = document.getElementById("userAreaEmail");
  const logoutLink = document.getElementById("logoutLink");
  const queryForm = document.getElementById("queryForm");

  if (userName) userName.textContent = user.username;
  if (userAreaName) userAreaName.textContent = user.username;
  if (userAreaEmail) userAreaEmail.textContent = user.email;

  if (logoutLink) {
    logoutLink.addEventListener("click", function (event) {
      event.preventDefault();
      clearUserSession();
      window.location.href = "login.html";
    });
  }

  if (queryForm) {
    queryForm.addEventListener("submit", handleQuery);
  }

  loadSubscriptions();
}

document.addEventListener("DOMContentLoaded", function () {
  const page = getCurrentPage();

  if (page === "login.html" || page === "") {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) loginForm.addEventListener("submit", handleLogin);
  }

  if (page === "register.html") {
    const registerForm = document.getElementById("registerForm");
    if (registerForm) registerForm.addEventListener("submit", handleRegister);
  }

  if (page === "main.html") {
    setupMainPage();
  }
});