// Add event listener for transaction type selection
document.addEventListener('DOMContentLoaded', function() {
    const typeSelect = document.getElementById('type');
    const categorySelect = document.getElementById('category');
    
    if (typeSelect && categorySelect) {
        typeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            const options = categorySelect.getElementsByTagName('optgroup');
            
            for (let optgroup of options) {
                if (selectedType === 'income' && optgroup.label === 'Income Categories') {
                    optgroup.style.display = '';
                    if (optgroup.getElementsByTagName('option')[0]) {
                        optgroup.getElementsByTagName('option')[0].selected = true;
                    }
                } else if (selectedType === 'expense' && optgroup.label === 'Expense Categories') {
                    optgroup.style.display = '';
                    if (optgroup.getElementsByTagName('option')[0]) {
                        optgroup.getElementsByTagName('option')[0].selected = true;
                    }
                } else {
                    optgroup.style.display = 'none';
                }
            }
        });
        
        // Trigger change event on load
        typeSelect.dispatchEvent(new Event('change'));
    }
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.getElementsByClassName('alert');
    for (let alert of alerts) {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    }
});
