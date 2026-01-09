/* static/js/script.js */

// 1. GENERIC SEARCH FUNCTION
const handleInput = (inputElement, listId, dataArray) => {
    const inputValue = inputElement.value.trim();
    const parentElement = document.getElementById(listId);
    parentElement.innerHTML = '';

    let matchingWords = dataArray.filter(word => word.toLowerCase().includes(inputValue.toLowerCase()));

    matchingWords.sort((a, b) => {
        return a.toLowerCase().indexOf(inputValue.toLowerCase()) - b.toLowerCase().indexOf(inputValue.toLowerCase());
    });

    matchingWords.forEach(word => {
        createListItem(word, parentElement, inputElement, false);
    });

    const exactMatchExists = dataArray.some(word => word.toLowerCase() === inputValue.toLowerCase());
    if (inputValue && !exactMatchExists) {
        createListItem(inputValue, parentElement, inputElement, true);
    }
};

function createListItem(word, parent, targetInput, isNew) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.classList.add("dropdown-item");
    a.href = "#";
    if (isNew) {
        a.innerHTML = `<span class="text-primary fw-bold">+ Add "${word}"</span>`;
    } else {
        a.textContent = word;
    }
    a.onclick = function (e) {
        e.preventDefault();
        targetInput.value = word;
    };
    li.appendChild(a);
    parent.appendChild(li);
}

// 2. FORMATTING HELPER
const format = (num) => {
    return num.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
};

// 3. BALANCE CALCULATION
function calculateBalance() {
    // Get Values
    const inv = parseFloat(document.getElementById('invAmt').value) || 0;
    const rec = parseFloat(document.getElementById('recAmt').value) || 0;
    const tds1 = parseFloat(document.getElementById('tds1').value) || 0;
    const tds2 = parseFloat(document.getElementById('tds2').value) || 0;

    const balance = inv - rec - tds1 - tds2;

    // Update Right Side Summary Table
    document.getElementById('summaryInvoiced').textContent = format(inv);
    document.getElementById('summaryReceived').textContent = format(rec);
    document.getElementById('summaryTDS1').textContent = format(tds1);
    document.getElementById('summaryTDS2').textContent = format(tds2);

    const balEl = document.getElementById('summaryBalance');
    balEl.textContent = format(balance);

    // Visual Logic
    if (balance <= 0.01) { 
        balEl.parentElement.classList.remove('text-danger');
        balEl.parentElement.classList.add('text-success');
    } else {
        balEl.parentElement.classList.remove('text-success');
        balEl.parentElement.classList.add('text-danger');
    }

    // Update Hidden Input for Flask
    document.getElementById('balanceHidden').value = balance.toFixed(2);
}

// 4. AUTO DATE (Updated)
document.addEventListener("DOMContentLoaded", function () {
    const dateInput = document.getElementById('dateInput');
    
    // CHECK FIRST: Is the box empty?
    // If it has a value (from the database), do NOT touch it.
    if(dateInput && !dateInput.value) {
        dateInput.valueAsDate = new Date();
    }
});