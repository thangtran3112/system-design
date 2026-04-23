import TodoItem from "./TodoItem";
function TodoList({ todos, onDelete }) {
  if (todos.length === 0) {
    return <p>No Todos yet. add one above!</p>;
  }

  return (
    <ul>
      {todos.map((todo) => (
        <TodoItem
          key={todo.id}
          id={todo.id}
          title={todo.title}
          description={todo.description}
          completed={todo.completed}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}

export default TodoList;
