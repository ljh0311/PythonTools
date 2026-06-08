/**
 * Calculation Utility Functions
 * Shared utilities for mathematical calculations and data processing
 */

/**
 * Calculate percentage change between two values
 */
export function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) {
    return current > 0 ? 100 : 0;
  }
  return Math.round(((current - previous) / previous) * 100);
}

/**
 * Calculate percentage (current / total * 100)
 */
export function calculatePercentage(current: number, total: number): number {
  if (total === 0) return 0;
  return Math.min(Math.round((current / total) * 100), 100);
}

/**
 * Round to specified decimal places
 */
export function roundToDecimal(value: number, decimals: number = 2): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

/**
 * Calculate average from array of numbers
 */
export function calculateAverage(values: number[]): number {
  if (values.length === 0) return 0;
  const sum = values.reduce((acc, val) => acc + val, 0);
  return sum / values.length;
}

/**
 * Calculate sum from array of numbers
 */
export function calculateSum(values: number[]): number {
  return values.reduce((acc, val) => acc + val, 0);
}

/**
 * Get maximum value from array
 */
export function getMax(values: number[]): number {
  return values.length > 0 ? Math.max(...values) : 0;
}

/**
 * Get minimum value from array
 */
export function getMin(values: number[]): number {
  return values.length > 0 ? Math.min(...values) : 0;
}

/**
 * Clamp value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Convert minutes to hours (decimal)
 */
export function minutesToHours(minutes: number): number {
  return roundToDecimal(minutes / 60, 1);
}

/**
 * Convert hours to minutes
 */
export function hoursToMinutes(hours: number): number {
  return Math.round(hours * 60);
}

/**
 * Calculate streak (consecutive days)
 */
export function calculateStreak(dates: Date[]): number {
  if (dates.length === 0) return 0;
  
  const uniqueDates = dates
    .map(d => d.toDateString())
    .filter((date, index, self) => self.indexOf(date) === index)
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
  
  if (uniqueDates.length === 0) return 0;
  
  let streak = 0;
  const today = new Date().toDateString();
  let expectedDate = new Date(today);
  
  for (const dateStr of uniqueDates) {
    const expectedDateStr = expectedDate.toDateString();
    
    if (dateStr === expectedDateStr) {
      streak++;
      expectedDate.setDate(expectedDate.getDate() - 1);
    } else if (streak === 0 && dateStr === today) {
      streak = 1;
      expectedDate.setDate(expectedDate.getDate() - 1);
    } else {
      break;
    }
  }
  
  return streak;
}

