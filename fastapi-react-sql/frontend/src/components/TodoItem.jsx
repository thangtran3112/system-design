function TodoItem({ id, title, description, completed, onDelete }) {
  return (
    <li>
      <span style={{}}>
        <strong>{title}</strong>
        {description && <>- {description}</>}
      </span>
      <button type="button" onClick={() => onDelete(id)}>
        Delete
      </button>
    </li>
  );
}

export default TodoItem;
