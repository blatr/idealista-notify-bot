// Kanban Board - SortableJS initialization
// BASE_URL is set in board.html before this script loads

document.addEventListener('DOMContentLoaded', function() {
    var baseUrl = window.BASE_URL || '';
    // Initialize sortable for each column
    document.querySelectorAll('.sortable-column').forEach(function(column) {
        new Sortable(column, {
            group: 'listings',  // Allow dragging between columns
            animation: 150,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            handle: '.listing-card',

            // When card is dropped
            onEnd: function(evt) {
                const cardId = evt.item.dataset.id;
                const newStage = evt.to.dataset.stage;
                const newIndex = evt.newIndex;

                // Get all card IDs in the new column for ordering
                const cardIds = Array.from(evt.to.children)
                    .filter(el => el.classList.contains('listing-card'))
                    .map(card => parseInt(card.dataset.id));

                // Update stage via API
                fetch(baseUrl + `/api/listings/${cardId}/stage`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        stage: newStage,
                        position: newIndex
                    })
                })
                .then(response => {
                    if (response.ok) {
                        // Update column counts
                        updateColumnCounts();
                    } else {
                        // Revert on error
                        console.error('Failed to update stage');
                        showToast('Failed to move card', 'error');
                    }
                })
                .catch(err => {
                    console.error('Error:', err);
                    showToast('Network error', 'error');
                });

                // Reorder the column
                if (cardIds.length > 1) {
                    fetch(baseUrl + `/api/listings/reorder/${newStage}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({card_ids: cardIds})
                    });
                }
            }
        });
    });

    // Update column card counts
    function updateColumnCounts() {
        document.querySelectorAll('.sortable-column').forEach(function(column) {
            const stage = column.dataset.stage;
            const count = column.querySelectorAll('.listing-card').length;
            const countEl = document.getElementById(`count-${stage}`);
            if (countEl) {
                countEl.textContent = count;
            }
        });
    }
});
