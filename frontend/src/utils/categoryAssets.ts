import grainsImg from '../assets/categories/grains-flour.jpg';
import tubersImg from '../assets/categories/fresh-tubers.jpg';
import oilsImg from '../assets/categories/oils-seasonings.jpg';
import proteinsImg from '../assets/categories/proteins-beef.jpg';

export function getCategoryFallbackImage(slug?: string, name?: string): string {
  const normalized = `${slug || ''} ${name || ''}`.toLowerCase();

  // Fresh tubers, cassava, and produce
  if (
    normalized.includes('tuber') ||
    normalized.includes('yam') ||
    normalized.includes('plantain') ||
    normalized.includes('cassava') ||
    normalized.includes('garri') ||
    normalized.includes('produce')
  ) {
    return tubersImg;
  }

  // Meats, seafood, and poultry
  if (
    normalized.includes('meat') ||
    normalized.includes('fish') ||
    normalized.includes('seafood') ||
    normalized.includes('beef') ||
    normalized.includes('chicken') ||
    normalized.includes('goat') ||
    normalized.includes('protein') ||
    normalized.includes('crayfish') ||
    normalized.includes('stockfish')
  ) {
    return proteinsImg;
  }

  // Oils, seasonings, spices, and cooking soup ingredients
  if (
    normalized.includes('oil') ||
    normalized.includes('spice') ||
    normalized.includes('season') ||
    normalized.includes('soup') ||
    normalized.includes('stew') ||
    normalized.includes('cooking') ||
    normalized.includes('ingredient') ||
    normalized.includes('drink') ||
    normalized.includes('beverage') ||
    normalized.includes('zobo')
  ) {
    return oilsImg;
  }

  // Grains, flours, beans, noodles, breakfast, and snacks
  return grainsImg;
}
