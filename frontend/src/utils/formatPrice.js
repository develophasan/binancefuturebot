/**
 * Format price with appropriate decimal places based on value
 */
export const formatPrice = (price) => {
  if (!price || isNaN(price)) return '0.00';
  
  const num = parseFloat(price);
  
  if (num >= 1000) {
    // BTC-like: $50,000 → 2 decimals
    return num.toFixed(2);
  } else if (num >= 100) {
    // ETH-like: $3,000 → 2 decimals
    return num.toFixed(2);
  } else if (num >= 1) {
    // BNB-like: $500 → 2 decimals
    return num.toFixed(2);
  } else if (num >= 0.1) {
    // Mid-range: $0.50 → 4 decimals
    return num.toFixed(4);
  } else if (num >= 0.01) {
    // Low-range: $0.05 → 6 decimals
    return num.toFixed(6);
  } else if (num >= 0.001) {
    // Very low: $0.005 → 6 decimals
    return num.toFixed(6);
  } else {
    // Extremely low: $0.00001 → 8 decimals
    return num.toFixed(8);
  }
};

/**
 * Format PnL with appropriate decimal places
 */
export const formatPnL = (pnl) => {
  if (!pnl || isNaN(pnl)) return '0.00';
  
  const num = parseFloat(pnl);
  const abs = Math.abs(num);
  
  if (abs >= 10) {
    return num.toFixed(2);
  } else if (abs >= 1) {
    return num.toFixed(3);
  } else if (abs >= 0.1) {
    return num.toFixed(4);
  } else {
    return num.toFixed(6);
  }
};

/**
 * Format percentage with high precision
 */
export const formatPercent = (percent) => {
  if (!percent || isNaN(percent)) return '0.00';
  
  const num = parseFloat(percent);
  const abs = Math.abs(num);
  
  if (abs >= 10) {
    return num.toFixed(2);
  } else if (abs >= 1) {
    return num.toFixed(3);
  } else {
    return num.toFixed(4);
  }
};
