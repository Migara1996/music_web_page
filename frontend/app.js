const API_BASE_URL = "http://music-projectALB-1110571390.us-east-1.elb.amazonaws.com";


/**
 * Source: JavaScript Tutorial
 * Adapted from: Adapted from: https://www.geeksforgeeks.org/javascript/javascript-tutorial/
 * Modified for: creating our js file  
*/

//  Utility: Identifies the current view to trigger relevant page-specific logic
 function getCurrentPage() {
  return window.location.pathname.split("/").pop();
}

/**
 * Session Management: Uses sessionStorage to persist user identity across views
 * Source: MDN Web Docs - Window.sessionStorage
 * Adapted from: (https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)
 */
function saveUserSession(user) {
  sessionStorage.setItem("user", JSON.stringify(user));
}

function getUserSession() {
  const user = sessionStorage.getItem("user");
  return user ? JSON.parse(user) : null;
}

//UI Cleanup: Ensures input fields are cleared to prevent stale data display.
function clearLoginForm() {
  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");

  if (emailInput) emailInput.value = "";
  if (passwordInput) passwordInput.value = "";
}

function clearUserSession() {
  sessionStorage.clear();
}

/**
 * Authentication: Handles Login form submission via Async Fetch
 * Source: MDN Web Docs - Using the Fetch API
 * Adapted from: (https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
 */
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


//Authentication: Handles New User Registration
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

/**
 * Dynamic UI Template: Generates the HTML card structure for song items
 * Uses template literals for clean property injection
 */
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


 //Data Retrieval: Fetches and renders the user's current music subscriptions
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

/**
 * Search Logic: Queries the music table based on user input
 * Filters are appended as URL parameters for the GET request
 */
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

//Write Operation: Adds a song to the user's DynamoDB subscription table
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

//Delete Operation: Removes a song from the user's subscriptions
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

//Initialization: Populates user data and attaches listeners for main.html
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
      // window.location.href = "login.html";
      window.location.replace("login.html");

    });
  }

  if (queryForm) {
    queryForm.addEventListener("submit", handleQuery);
  }

  loadSubscriptions();
}

//Entry Point: Route-based event listener registration
document.addEventListener("DOMContentLoaded", function () {
  const page = getCurrentPage();

  if (page === "login.html" || page === "") {
    clearLoginForm();

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

//Navigation Guard: Ensures forms are cleared and sessions are valid on history navigation
window.addEventListener("pageshow", function () {
  const page = getCurrentPage();

  if (page === "login.html" || page === "") {
    clearLoginForm();
  }

  if (page === "main.html") {
    const user = getUserSession();

    if (!user) {
      window.location.replace("login.html");
    }
  }
});