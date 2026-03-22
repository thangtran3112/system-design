import { useState } from "react";
import TodoForm from "./components/TodoForm";
import TodoList from "./components/TodoList";

const FAKE_TODOS = [
  {
    id: 1,
    title: "Learn React",
    description: "Components and JSX",
    completed: false,
  },
  {
    id: 2,
    title: "Learn FastAPI",
    description: "Already done!",
    completed: true,
  },
];

function App() {
  const [todos, setTodos] = useState([]);
  const handleDelete = (id) => {
    setTodos(todos.filter((todo) => todo.id !== id));
  };

  const handleAdd = (newTodo) => {
    const todo = { ...newTodo, id: Date.now(), completed: false };
    setTodos([...todos, todo]);
  };

  return (
    <div>
      <h1>Todo App</h1>
      <TodoForm onAdd={handleAdd} />
      <TodoList todos={todos} onDelete={handleDelete} />
    </div>
  );
}

export default App;
