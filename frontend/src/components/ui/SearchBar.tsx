import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import './SearchBar.css';

interface SearchBarProps {
  initialValue?: string;
  onSearch: (query: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  initialValue = '',
  onSearch,
  placeholder = 'Search products',
  autoFocus = false,
  size = 'md',
  fullWidth = true,
}) => {
  const [query, setQuery] = useState(initialValue);

  useEffect(() => {
    setQuery(initialValue);
  }, [initialValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query.trim());
  };

  const handleClear = () => {
    setQuery('');
    onSearch('');
  };

  return (
    <form
      className={`search-bar search-bar--${size} ${fullWidth ? 'search-bar--full' : ''}`}
      onSubmit={handleSubmit}
      role="search"
    >
      <div className="search-bar__input-wrapper">
        <Search className="search-bar__icon" size={18} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="search-bar__input"
          autoFocus={autoFocus}
          aria-label="Search products"
        />
        {query && (
          <button
            type="button"
            className="search-bar__clear"
            onClick={handleClear}
            aria-label="Clear search query"
          >
            <X size={16} />
          </button>
        )}
      </div>
      <button type="submit" className="search-bar__submit" aria-label="Submit search">
        Search
      </button>
    </form>
  );
};
