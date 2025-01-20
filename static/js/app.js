    const showInput = document.getElementById('showInput');
    const autocompleteList = document.getElementById('autocomplete');
    const findEpisodeButton = document.getElementById('findEpisode');

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
    document.getElementById('poster').src = data.poster || '';
  } catch (error) {
    alert(`Error: ${error.message}`);
    outputDiv.style.display = 'none';
  } finally {
    // Hide the loading overlay
    loadingOverlay.style.display = 'none';
  }
});
