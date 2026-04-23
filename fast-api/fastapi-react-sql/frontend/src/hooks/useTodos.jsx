import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

function useTodos() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTodos() {
      try {
        const res = await fetch(`${API}/todos`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setTodos(await res.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchTodos();
  }, []);

  const addTodo = async (newTodo) => {
    const res = await fetch(`${API}/todos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newTodo),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const created = await res.json();
    setTodos((prev) => [...prev, created]);
    return created;
  };

  const updateTodo = async (id, updateFields) => {
    // in some case, we need url encode for id, if it has special characters or space
    const res = await fetch(`${API}/todos/${id}`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updateFields),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const updated = await res.json();
    setTodos((prev) => {
      const otherTodos = prev.filter((todo) => todo.id !== id);
      return [...otherTodos, updated];
    });

    return updated;
  };

  const deleteTodo = async (id) => {
    const res = await fetch(`${API}/todos/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    setTodos((prev) => prev.filter((todo) => todo.id !== id));
  };

  return { todos, isLoading, error, addTodo, updateTodo, deleteTodo };
}

export default useTodos;
