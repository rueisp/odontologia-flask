/**
 * Autocomplete component for CUPS and CIE-10 codes
 * Provides search-as-you-type functionality
 */

class Autocomplete {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.apiUrl = options.apiUrl;
        this.minChars = options.minChars || 2;
        this.onSelect = options.onSelect || (() => {});
        this.valueField = options.valueField || 'code';
        this.labelField = options.labelField || 'label';
        
        this.resultsContainer = null;
        this.selectedIndex = -1;
        this.results = [];
        
        this.init();
    }
    
    init() {
        // Create results container
        this.resultsContainer = document.createElement('div');
        this.resultsContainer.className = 'autocomplete-results';
        this.resultsContainer.style.cssText = `
            position: absolute;
            z-index: 1000;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            max-height: 300px;
            overflow-y: auto;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        
        // Insert after input
        this.input.parentNode.style.position = 'relative';
        this.input.parentNode.appendChild(this.resultsContainer);
        
        // Event listeners
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        this.input.addEventListener('blur', () => {
            setTimeout(() => this.hideResults(), 200);
        });
    }
    
    async handleInput(e) {
        const query = e.target.value.trim();
        
        if (query.length < this.minChars) {
            this.hideResults();
            return;
        }
        
        try {
            const response = await fetch(`${this.apiUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.results = data;
            this.showResults();
        } catch (error) {
            console.error('Autocomplete error:', error);
        }
    }
    
    showResults() {
        if (this.results.length === 0) {
            this.hideResults();
            return;
        }
        
        this.resultsContainer.innerHTML = '';
        this.selectedIndex = -1;
        
        this.results.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            `;
            div.textContent = item[this.labelField];
            div.dataset.index = index;
            
            div.addEventListener('mouseenter', () => {
                this.selectItem(index);
            });
            
            div.addEventListener('click', () => {
                this.chooseItem(index);
            });
            
            this.resultsContainer.appendChild(div);
        });
        
        this.resultsContainer.style.display = 'block';
        this.resultsContainer.style.width = this.input.offsetWidth + 'px';
    }
    
    hideResults() {
        this.resultsContainer.style.display = 'none';
        this.selectedIndex = -1;
    }
    
    selectItem(index) {
        const items = this.resultsContainer.querySelectorAll('.autocomplete-item');
        items.forEach(item => item.style.backgroundColor = '');
        
        if (index >= 0 && index < items.length) {
            items[index].style.backgroundColor = '#f0f0f0';
            this.selectedIndex = index;
        }
    }
    
    chooseItem(index) {
        if (index >= 0 && index < this.results.length) {
            const item = this.results[index];
            this.input.value = item[this.valueField];
            this.onSelect(item);
            this.hideResults();
        }
    }
    
    handleKeydown(e) {
        if (this.resultsContainer.style.display === 'none') return;
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectItem(Math.min(this.selectedIndex + 1, this.results.length - 1));
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectItem(Math.max(this.selectedIndex - 1, 0));
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.chooseItem(this.selectedIndex);
                }
                break;
            case 'Escape':
                this.hideResults();
                break;
        }
    }
}

// Export for use in other scripts
window.Autocomplete = Autocomplete;
