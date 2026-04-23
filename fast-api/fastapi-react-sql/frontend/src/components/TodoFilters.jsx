function TodoFilters({
  search,
  onSearchChange,
  filter,
  onFilterChange,
  sortBy,
  onSortChange,
}) {
  return (
    <div>
      <div>
        <label htmlFor="search">Search</label>
        <input
          id="search"
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter by title..."
        />
      </div>

      <div>
        <label htmlFor="filter-status">Status</label>
        <select
          id="filter-status"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <fieldset>
        <legend>Sort by</legend>
        <label>
          <input
            type="radio"
            name="sortBy"
            value="title"
            checked={sortBy === "title"}
            onChange={(e) => onSortChange(e.target.value)}
          />
          Title
        </label>
        <label>
          <input
            type="radio"
            name="sortBy"
            value="id"
            checked={sortBy === "id"}
            onChange={(e) => onSortChange(e.target.value)}
          />
          Date added
        </label>
      </fieldset>
    </div>
  );
}

export default TodoFilters;
