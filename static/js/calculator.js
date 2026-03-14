// SIP Calculator functionality for WealthWise
let sipChart = null;

// Initialize calculator
function initCalculator() {
  // Set up event listeners for sliders
  const monthlySlider = document.getElementById('monthly-amount');
  const returnSlider = document.getElementById('annual-return');
  const yearsSlider = document.getElementById('investment-years');

  if (monthlySlider) {
    monthlySlider.addEventListener('input', updateCalculator);
    updateSliderValue('monthly-amount', 'monthly-value', '₹', formatCurrency);
  }

  if (returnSlider) {
    returnSlider.addEventListener('input', updateCalculator);
    updateSliderValue('annual-return', 'return-value', '', (val) => val + '%');
  }

  if (yearsSlider) {
    yearsSlider.addEventListener('input', updateCalculator);
    updateSliderValue('investment-years', 'years-value', '', (val) => val + ' years');
  }

  // Initial calculation
  updateCalculator();
}

// Update slider value display
function updateSliderValue(sliderId, valueId, prefix = '', formatter = (val) => val) {
  const slider = document.getElementById(sliderId);
  const valueDisplay = document.getElementById(valueId);

  if (slider && valueDisplay) {
    const updateValue = () => {
      valueDisplay.textContent = prefix + formatter(slider.value);
    };

    slider.addEventListener('input', updateValue);
    updateValue(); // Initial update
  }
}

// Update calculator results
async function updateCalculator() {
  const monthlyAmount = parseFloat(document.getElementById('monthly-amount')?.value) || 5000;
  const annualReturn = parseFloat(document.getElementById('annual-return')?.value) || 12;
  const years = parseInt(document.getElementById('investment-years')?.value) || 10;

  try {
    const response = await fetch('/api/calculator', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        monthly_amount: monthlyAmount,
        annual_return_pct: annualReturn,
        years: years
      })
    });

    const data = await response.json();

    if (data.status === 'success') {
      updateResultsDisplay(data);
      updateChart(data.chart);
      updateTable(data.table_data);
    } else {
      throw new Error(data.message || 'Failed to calculate SIP');
    }
  } catch (error) {
    console.error('Error calculating SIP:', error);
    showToast('Failed to calculate SIP', 'error');
  }
}

// Update results display
function updateResultsDisplay(data) {
  const summary = data.summary;

  // Update result cards
  updateElement('total-invested', formatCurrency(summary.total_invested));
  updateElement('portfolio-value', formatCurrency(summary.portfolio_value));
  updateElement('compounding-gain', formatCurrency(summary.compounding_gain));
}

// Update chart
function updateChart(chartData) {
  const ctx = document.getElementById('sip-chart');
  if (!ctx) return;

  // Destroy existing chart
  if (sipChart) {
    sipChart.destroy();
  }

  sipChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartData.years,
      datasets: [
        {
          label: 'Amount Invested',
          data: chartData.invested,
          borderColor: '#F5A623',
          backgroundColor: 'rgba(245, 166, 35, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4
        },
        {
          label: 'Portfolio Value',
          data: chartData.portfolio_value,
          borderColor: '#00C9B1',
          backgroundColor: 'rgba(0, 201, 177, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return formatCurrency(value);
            }
          }
        }
      }
    }
  });
}

// Update results table
function updateTable(tableData) {
  const tbody = document.getElementById('results-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';

  tableData.forEach(row => {
    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td>${row.year}</td>
      <td>${formatCurrency(row.invested)}</td>
      <td>${formatCurrency(row.portfolio_value)}</td>
      <td>${formatCurrency(row.gain)}</td>
    `;

    tbody.appendChild(tr);
  });
}

// Utility functions
function updateElement(id, content) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = content;
  }
}

function formatCurrency(amount) {
  if (!amount) return '₹0';

  const absAmount = Math.abs(amount);

  if (absAmount >= 10000000) {
    return '₹' + (Math.round(amount / 10000000 * 100) / 100) + 'Cr';
  } else if (absAmount >= 100000) {
    return '₹' + (Math.round(amount / 100000 * 100) / 100) + 'L';
  } else if (absAmount >= 1000) {
    return '₹' + (Math.round(amount / 1000 * 100) / 100) + 'K';
  } else {
    return '₹' + Math.round(amount);
  }
}

function showToast(message, type = 'info') {
  // Simple toast implementation
  console.log(`${type.toUpperCase()}: ${message}`);
  // You can implement a proper toast system here
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initCalculator();
});
