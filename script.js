var cityInput = document.getElementById("searchCity");

// ✅ Add OpenWeatherMap API Key here
var weatherAPIKey = "";

// ✅ Random Background
var backgroundsList = [
  "day1.jpg",
  "day2.jpg",
  "day3.jpg",
  "day3.jpg",
  "day1.jpg",
  "cloudy1.jpg",
  "cloudy2.jpg",
  "cloudy3.jpg",
  "cloudy4.jpg",
  "cloudy4.jpg",
];

var randomBackground = backgroundsList[Math.floor(Math.random() * backgroundsList.length)];

document.body.style.background =
  "linear-gradient(rgba(0, 0, 0, 0.5),rgba(0, 0, 0, 0.5)) , url('media/" +
  randomBackground +
  "')";

// ✅ OpenWeather API Weather + Forecast
async function getWeather(cityInputValue) {
  var unit = "metric";
  var apiUrl = `https://api.openweathermap.org/data/2.5/weather?q=${cityInputValue}&appid=${weatherAPIKey}&units=${unit}`;

  var response = await fetch(apiUrl);
  var data = await response.json();

  if (!data || data.cod == 404) {
    document.getElementById("locationName").innerHTML = "City Not Found ❌";
    return;
  }

  document.getElementById("locationName").innerHTML = data.name;
  document.getElementById("temperatureValue").innerHTML =
    Math.round(data.main.temp) + "<sup>o</sup>C";
  document.getElementById("weatherType").innerHTML = data.weather[0].description;

  document.getElementById("realFeelAdditionalValue").innerHTML =
    Math.round(data.main.feels_like) + "<sup>o</sup>C";
  document.getElementById("windSpeedAdditionalValue").innerHTML =
    data.wind.speed + " km/h";
  document.getElementById("windDirectionAdditionalValue").innerHTML =
    data.wind.deg;
  document.getElementById("visibilityAdditionalValue").innerHTML =
    data.visibility / 1000 + " km";
  document.getElementById("pressureAdditionalValue").innerHTML =
    data.main.pressure;
  document.getElementById("maxTemperatureAdditionalValue").innerHTML =
    Math.round(data.main.temp_max) + "<sup>o</sup>C";
  document.getElementById("minTemperatureAdditionalValue").innerHTML =
    Math.round(data.main.temp_min) + "<sup>o</sup>C";
  document.getElementById("humidityAdditionalValue").innerHTML =
    data.main.humidity + "%";
  document.getElementById("sunriseAdditionalValue").innerHTML =
    new Date(data.sys.sunrise * 1000).toLocaleTimeString();
  document.getElementById("sunsetAdditionalValue").innerHTML =
    new Date(data.sys.sunset * 1000).toLocaleTimeString();

  loadForecast(cityInputValue);
  loadInsights(cityInputValue);
}

// ✅ 5-day Forecast
async function loadForecast(city) {
  const forecastContainer = document.getElementById("forecast-container");
  forecastContainer.innerHTML = "";

  fetch(
    `https://api.openweathermap.org/data/2.5/forecast?q=${city}&appid=${weatherAPIKey}&units=metric`
  )
    .then((response) => response.json())
    .then((data) => {
      const dailyForecasts = {};

      data.list.forEach((entry) => {
        const dateTime = new Date(entry.dt * 1000);
        const date = dateTime.toLocaleDateString("en-US", {
          weekday: "short",
          day: "numeric",
        });

        if (!dailyForecasts[date]) {
          dailyForecasts[date] = {
            date: date,
            icon: `https://openweathermap.org/img/w/${entry.weather[0].icon}.png`,
            maxTemp: -Infinity,
            minTemp: Infinity,
            weatherType: entry.weather[0].main,
          };
        }

        if (entry.main.temp_max > dailyForecasts[date].maxTemp)
          dailyForecasts[date].maxTemp = entry.main.temp_max;

        if (entry.main.temp_min < dailyForecasts[date].minTemp)
          dailyForecasts[date].minTemp = entry.main.temp_min;
      });

      Object.values(dailyForecasts).forEach((day) => {
        const forecastCard = document.createElement("div");
        forecastCard.classList.add("daily-forecast-card");

        forecastCard.innerHTML = `
          <p class="daily-forecast-date">${day.date}</p>
          <div class="daily-forecast-logo"><img class="imgs-as-icons" src="${day.icon}"></div>
          <div class="max-min-temperature-daily-forecast">
            <span class="max-daily-forecast">${Math.round(day.maxTemp)}<sup>o</sup>C</span>
            <span class="min-daily-forecast">${Math.round(day.minTemp)}<sup>o</sup>C</span>
          </div>
          <p class="weather-type-daily-forecast">${day.weatherType}</p>
        `;
        forecastContainer.appendChild(forecastCard);
      });
    })
    .catch((error) => console.error("Error fetching forecast:", error));
}

// ✅ Backend Insights + Graphs + Anomalies
async function loadInsights(city) {
  try {
    const dataRes = await fetch(`http://127.0.0.1:5000/api/insights?city=${city}`);
    const data = await dataRes.json();

    document.getElementById("insightsContainer").innerHTML = `
      <p><b>Records:</b> ${data.records}</p>
      <p><b>Avg Temp:</b> ${data.mean_temp}°C</p>
      <p><b>Min Temp:</b> ${data.min_temp}°C</p>
      <p><b>Max Temp:</b> ${data.max_temp}°C</p>
    `;

    document.getElementById("trendGraph").src =
      `http://127.0.0.1:5000/api/graph?city=${city}&_=${Date.now()}`;

    document.getElementById("forecastGraph").src =
      `http://127.0.0.1:5000/api/forecast_graph?city=${city}&_=${Date.now()}`;

    const anomalyRes = await fetch(
      `http://127.0.0.1:5000/api/anomalies?city=${city}`
    );
    const anomalies = await anomalyRes.json();

    let table = `<tr><th>Date</th><th>Temp</th></tr>`;
    anomalies.forEach((a) => {
      table += `<tr><td>${a.date}</td><td>${a.temperature}°C</td></tr>`;
    });

    document.getElementById("anomalyTable").innerHTML = table;
  } catch (err) {
    console.error(err);
  }
}

// ✅ Search Trigger
cityInput.addEventListener("keyup", function (event) {
  if (event.key === "Enter") {
    let city = cityInput.value;
    if (city !== "") getWeather(city);
  }
});

// ✅ Reset
document.getElementById("resetBtn").addEventListener("click", function (e) {
  e.preventDefault();
  location.reload();
});
