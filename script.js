
var weatherAPIKey = "fe93bcfdee45155c2f92f3f469baa855";


// 
const BASE_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:5000"
    : window.location.origin;

// 
const cityInput = document.getElementById("searchCity");

// 
const backgroundsList = [
  "day1.jpg",
  "day2.jpg",
  "day3.jpg",
  "cloudy1.jpg",
  "cloudy2.jpg",
  "cloudy3.jpg",
  "cloudy4.jpg"
];

const randomBackground = backgroundsList[Math.floor(Math.random() * backgroundsList.length)];
document.body.style.background =
  `linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5)), url('./media/${randomBackground}')`;
document.body.style.backgroundSize = "cover";
document.body.style.backgroundRepeat = "no-repeat";

// ✅ Fetch Live Weather
async function getWeather(cityInputValue) {
  if (!weatherAPIKey) {
    alert("❌ API Key missing! Add NEXT_PUBLIC_WEATHER_API_KEY in Vercel.");
    return;
  }

  const apiUrl =
    `https://api.openweathermap.org/data/2.5/weather?q=${cityInputValue}&appid=${weatherAPIKey}&units=metric`;

  const response = await fetch(apiUrl);
  const data = await response.json();

  if (data.cod != 200) {
    document.getElementById("locationName").innerHTML = "City Not Found ❌";
    return;
  }

  updateWeatherUI(data);
  loadForecast(cityInputValue);
  loadInsights(cityInputValue);
}

//
function updateWeatherUI(data) {
  document.getElementById("locationName").innerText = data.name;
  document.getElementById("temperatureValue").innerHTML =
    Math.round(data.main.temp) + "<sup>o</sup>C";
  document.getElementById("weatherType").innerText = data.weather[0].description;
  document.getElementById("realFeelAdditionalValue").innerHTML =
    Math.round(data.main.feels_like) + "<sup>o</sup>C";
  document.getElementById("windSpeedAdditionalValue").innerText =
    data.wind.speed + " km/h";
  document.getElementById("windDirectionAdditionalValue").innerText =
    data.wind.deg + "°";
  document.getElementById("visibilityAdditionalValue").innerText =
    (data.visibility / 1000).toFixed(1) + " km";
  document.getElementById("pressureAdditionalValue").innerText =
    data.main.pressure + " hPa";
  document.getElementById("maxTemperatureAdditionalValue").innerHTML =
    Math.round(data.main.temp_max) + "<sup>o</sup>C";
  document.getElementById("minTemperatureAdditionalValue").innerHTML =
    Math.round(data.main.temp_min) + "<sup>o</sup>C";
  document.getElementById("humidityAdditionalValue").innerText =
    data.main.humidity + "%";
  document.getElementById("sunriseAdditionalValue").innerText =
    new Date(data.sys.sunrise * 1000).toLocaleTimeString();
  document.getElementById("sunsetAdditionalValue").innerText =
    new Date(data.sys.sunset * 1000).toLocaleTimeString();
}


async function loadForecast(city) {
  const box = document.getElementById("forecast-container");
  box.innerHTML = "Loading forecast...";

  try {
    const res = await fetch(
      `https://api.openweathermap.org/data/2.5/forecast?q=${city}&appid=${weatherAPIKey}&units=metric`
    );
    const data = await res.json();

    box.innerHTML = "";
    const daily = {};

    data.list.forEach(entry => {
      const date = new Date(entry.dt * 1000).toLocaleDateString("en-US", {
        weekday: "short",
        day: "numeric"
      });

      if (!daily[date]) {
        daily[date] = {
          date,
          icon: `https://openweathermap.org/img/wn/${entry.weather[0].icon}.png`,
          max: entry.main.temp_max,
          min: entry.main.temp_min,
          type: entry.weather[0].main
        };
      }

      daily[date].max = Math.max(daily[date].max, entry.main.temp_max);
      daily[date].min = Math.min(daily[date].min, entry.main.temp_min);
    });

    Object.values(daily).forEach(day => {
      box.innerHTML += `
        <div class="daily-forecast-card">
          <p>${day.date}</p>
          <img src="${day.icon}" class="imgs-as-icons">
          <p>⬆ ${Math.round(day.max)}°C ⬇ ${Math.round(day.min)}°C</p>
          <p>${day.type}</p>
        </div>`;
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = "Forecast unavailable ❌";
  }
}

// ✅ Insights (Backend)
async function loadInsights(city) {
  try {
    const res = await fetch(`${BASE_URL}/api/insights?city=${city}`);
    const data = await res.json();

    document.getElementById("insightsContainer").innerHTML = `
      <b>Records:</b> ${data.records}<br>
      <b>Avg Temp:</b> ${data.mean_temp}°C<br>
      <b>Range:</b> ${data.min_temp}°C → ${data.max_temp}°C
    `;

    document.getElementById("trendGraph").src =
      `${BASE_URL}/api/graph?city=${city}&_=${Date.now()}`;

    document.getElementById("forecastGraph").src =
      `${BASE_URL}/api/forecast_graph?city=${city}&_=${Date.now()}`;
  } catch (e) {
    console.warn("Backend unavailable on Vercel ❌");
  }
}


cityInput.addEventListener("keyup", e => {
  if (e.key === "Enter") getWeather(cityInput.value);
});


document.getElementById("resetBtn").addEventListener("click", () => {
  location.reload();
});


getWeather("Mumbai");


