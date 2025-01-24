const showInput = document.getElementById('showInput');
const autocompleteList = document.getElementById('autocomplete');
const findEpisodeButton = document.getElementById('findEpisode');
const keywordInput = document.getElementById('keywordInput');

// Function to update the URL with query parameters
function updateURL(showName, keywords = '') {
  const url = new URL(window.location);
  url.searchParams.set('show', showName);  // Update or add the 'show' parameter
  if (keywords) {
    url.searchParams.set('keywords', keywords);  // Update or add the 'keywords' parameter if provided
  } else {
    url.searchParams.delete('keywords'); // Remove the 'keywords' parameter if it's empty
  }
  window.history.pushState({}, '', url);  // Update the URL in the browser without reloading
}

// Fetch suggestions from TMDb as the user types
showInput.addEventListener('input', async () => {
  const query = showInput.value.trim();
  autocompleteList.innerHTML = '';
  autocompleteList.style.display = 'none';

  if (query.length < 2) {
    console.log('Query too short');
    return; // Wait until the user types at least 2 characters
  }

  try {
    console.log(`Fetching autocomplete results for query: ${query}`);
    const response = await fetch(`/autocomplete?query=${encodeURIComponent(query)}`);
    if (!response.ok) {
      console.error('Failed to fetch autocomplete results');
      return;
    }

    const suggestions = await response.json();
    console.log('Autocomplete suggestions:', suggestions);

    if (suggestions.length > 0) {
      autocompleteList.style.display = 'block';
      suggestions.forEach(show => {
        const listItem = document.createElement('li');
        listItem.textContent = show.name;
        listItem.addEventListener('click', () => {
          showInput.value = show.name;
          autocompleteList.innerHTML = '';
          autocompleteList.style.display = 'none';
          updateURL(show.name, keywordInput.value.trim()); // Update URL with the selected show and keywords
        });
        autocompleteList.appendChild(listItem);
      });
    } else {
      console.log('No suggestions found');
    }
  } catch (error) {
    console.error('Error fetching autocomplete suggestions:', error);
  }
});

// Hide autocomplete when clicking outside
document.addEventListener('click', (event) => {
  if (!autocompleteList.contains(event.target) && event.target !== showInput) {
    autocompleteList.innerHTML = '';
    autocompleteList.style.display = 'none';
  }
});

// Fetch random episode when button is clicked
findEpisodeButton.addEventListener('click', async () => {
  const showName = showInput.value.trim();
  const keywords = keywordInput.value.trim();
  const outputDiv = document.getElementById('output');
  const loadingOverlay = document.getElementById('loading-overlay'); // Reference the overlay

  if (!showName) {
    alert('Please enter a TV show name.');
    return;
  }

  // Update the URL with the show name and keywords
  updateURL(showName, keywords);

  try {
    // Show the loading overlay
    loadingOverlay.style.display = 'flex';

    // Use the new filter endpoint with both show and keywords
    const response = await fetch(`/filter?showName=${encodeURIComponent(showName)}&keywords=${encodeURIComponent(keywords)}`);
    if (!response.ok) {
      throw new Error('Show not found, no episodes match the filters, or server error');
    }

    const data = await response.json();
    outputDiv.style.display = 'block';

    // Update the new Season xx Episode xx display
    const seasonEpisode = document.getElementById('season-episode');
    seasonEpisode.textContent = `Season ${data.season || 'N/A'} Episode ${data.episode || 'N/A'}`;

    // Update the remaining details
    document.getElementById('title').textContent = data.title || 'N/A';
    document.getElementById('synopsis').textContent = data.synopsis || 'No synopsis available.';

    // Handle missing images with an onerror fallback
    const poster = document.getElementById('poster');
    poster.src = data.poster || '/static/missing.png';
    poster.onerror = () => {
      poster.src = '/static/missing.png'; // Fallback to the missing image
    };
  } catch (error) {
    alert(`Error: ${error.message}`);
    outputDiv.style.display = 'none';
  } finally {
    // Hide the loading overlay
    loadingOverlay.style.display = 'none';
  }
});

// Pre-populate the input and fetch episode details if show and keywords are in the URL
window.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const showName = urlParams.get('show');
  const keywords = urlParams.get('keywords');

  if (showName) {
    showInput.value = showName;  // Pre-fill the input with the show name
    if (keywords) {
      keywordInput.value = keywords;  // Pre-fill the keywords input if present in the URL
    }
    findEpisodeButton.click();  // Automatically trigger the find episode action
  }
});
