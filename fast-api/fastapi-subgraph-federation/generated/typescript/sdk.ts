import { DocumentNode } from 'graphql';
import gql from 'graphql-tag';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
};

export type CreateTodoInput = {
  description?: Scalars['String']['input'];
  ownerId: Scalars['Int']['input'];
  title: Scalars['String']['input'];
};

export type CreateUserInput = {
  email: Scalars['String']['input'];
  name: Scalars['String']['input'];
  picture?: InputMaybe<Scalars['String']['input']>;
  provider?: Scalars['String']['input'];
};

export type Mutation = {
  __typename?: 'Mutation';
  createTodo: TodoType;
  createUser: UserType;
  deleteTodo: Scalars['Boolean']['output'];
  updateTodo?: Maybe<TodoType>;
};


export type MutationCreateTodoArgs = {
  input: CreateTodoInput;
};


export type MutationCreateUserArgs = {
  input: CreateUserInput;
};


export type MutationDeleteTodoArgs = {
  id: Scalars['Int']['input'];
};


export type MutationUpdateTodoArgs = {
  id: Scalars['Int']['input'];
  input: UpdateTodoInput;
};

export type Query = {
  __typename?: 'Query';
  todo?: Maybe<TodoType>;
  todos: Array<TodoType>;
  user?: Maybe<UserType>;
  users: Array<UserType>;
};


export type QueryTodoArgs = {
  id: Scalars['Int']['input'];
};


export type QueryTodosArgs = {
  ownerId?: InputMaybe<Scalars['Int']['input']>;
};


export type QueryUserArgs = {
  id: Scalars['Int']['input'];
};

export type TodoType = {
  __typename?: 'TodoType';
  completed: Scalars['Boolean']['output'];
  description: Scalars['String']['output'];
  id: Scalars['Int']['output'];
  owner: UserType;
  title: Scalars['String']['output'];
};

export type UpdateTodoInput = {
  completed?: InputMaybe<Scalars['Boolean']['input']>;
  description?: InputMaybe<Scalars['String']['input']>;
  title?: InputMaybe<Scalars['String']['input']>;
};

export type UserType = {
  __typename?: 'UserType';
  email: Scalars['String']['output'];
  id: Scalars['Int']['output'];
  name: Scalars['String']['output'];
  picture?: Maybe<Scalars['String']['output']>;
  provider: Scalars['String']['output'];
  todos: Array<TodoType>;
};

export type CreateTodoMutationVariables = Exact<{
  input: CreateTodoInput;
}>;


export type CreateTodoMutation = { __typename?: 'Mutation', createTodo: { __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean, owner: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string } } };

export type UpdateTodoMutationVariables = Exact<{
  id: Scalars['Int']['input'];
  input: UpdateTodoInput;
}>;


export type UpdateTodoMutation = { __typename?: 'Mutation', updateTodo?: { __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean, owner: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string } } | null };

export type DeleteTodoMutationVariables = Exact<{
  id: Scalars['Int']['input'];
}>;


export type DeleteTodoMutation = { __typename?: 'Mutation', deleteTodo: boolean };

export type CreateUserMutationVariables = Exact<{
  input: CreateUserInput;
}>;


export type CreateUserMutation = { __typename?: 'Mutation', createUser: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string, todos: Array<{ __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean }> } };

export type TodosQueryVariables = Exact<{
  ownerId?: InputMaybe<Scalars['Int']['input']>;
}>;


export type TodosQuery = { __typename?: 'Query', todos: Array<{ __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean, owner: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string } }> };

export type TodoQueryVariables = Exact<{
  id: Scalars['Int']['input'];
}>;


export type TodoQuery = { __typename?: 'Query', todo?: { __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean, owner: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string } } | null };

export type UsersQueryVariables = Exact<{ [key: string]: never; }>;


export type UsersQuery = { __typename?: 'Query', users: Array<{ __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string, todos: Array<{ __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean }> }> };

export type UserQueryVariables = Exact<{
  id: Scalars['Int']['input'];
}>;


export type UserQuery = { __typename?: 'Query', user?: { __typename?: 'UserType', id: number, email: string, name: string, picture?: string | null, provider: string, todos: Array<{ __typename?: 'TodoType', id: number, title: string, description: string, completed: boolean }> } | null };


export const CreateTodoDocument = gql`
    mutation CreateTodo($input: CreateTodoInput!) {
  createTodo(input: $input) {
    id
    title
    description
    completed
    owner {
      id
      email
      name
      picture
      provider
    }
  }
}
    `;
export const UpdateTodoDocument = gql`
    mutation UpdateTodo($id: Int!, $input: UpdateTodoInput!) {
  updateTodo(id: $id, input: $input) {
    id
    title
    description
    completed
    owner {
      id
      email
      name
      picture
      provider
    }
  }
}
    `;
export const DeleteTodoDocument = gql`
    mutation DeleteTodo($id: Int!) {
  deleteTodo(id: $id)
}
    `;
export const CreateUserDocument = gql`
    mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    todos {
      id
      title
      description
      completed
    }
    email
    name
    picture
    provider
  }
}
    `;
export const TodosDocument = gql`
    query Todos($ownerId: Int) {
  todos(ownerId: $ownerId) {
    id
    title
    description
    completed
    owner {
      id
      email
      name
      picture
      provider
    }
  }
}
    `;
export const TodoDocument = gql`
    query Todo($id: Int!) {
  todo(id: $id) {
    id
    title
    description
    completed
    owner {
      id
      email
      name
      picture
      provider
    }
  }
}
    `;
export const UsersDocument = gql`
    query Users {
  users {
    id
    todos {
      id
      title
      description
      completed
    }
    email
    name
    picture
    provider
  }
}
    `;
export const UserDocument = gql`
    query User($id: Int!) {
  user(id: $id) {
    id
    todos {
      id
      title
      description
      completed
    }
    email
    name
    picture
    provider
  }
}
    `;
export type Requester<C = {}> = <R, V>(doc: DocumentNode, vars?: V, options?: C) => Promise<R> | AsyncIterable<R>
export function getSdk<C>(requester: Requester<C>) {
  return {
    CreateTodo(variables: CreateTodoMutationVariables, options?: C): Promise<CreateTodoMutation> {
      return requester<CreateTodoMutation, CreateTodoMutationVariables>(CreateTodoDocument, variables, options) as Promise<CreateTodoMutation>;
    },
    UpdateTodo(variables: UpdateTodoMutationVariables, options?: C): Promise<UpdateTodoMutation> {
      return requester<UpdateTodoMutation, UpdateTodoMutationVariables>(UpdateTodoDocument, variables, options) as Promise<UpdateTodoMutation>;
    },
    DeleteTodo(variables: DeleteTodoMutationVariables, options?: C): Promise<DeleteTodoMutation> {
      return requester<DeleteTodoMutation, DeleteTodoMutationVariables>(DeleteTodoDocument, variables, options) as Promise<DeleteTodoMutation>;
    },
    CreateUser(variables: CreateUserMutationVariables, options?: C): Promise<CreateUserMutation> {
      return requester<CreateUserMutation, CreateUserMutationVariables>(CreateUserDocument, variables, options) as Promise<CreateUserMutation>;
    },
    Todos(variables?: TodosQueryVariables, options?: C): Promise<TodosQuery> {
      return requester<TodosQuery, TodosQueryVariables>(TodosDocument, variables, options) as Promise<TodosQuery>;
    },
    Todo(variables: TodoQueryVariables, options?: C): Promise<TodoQuery> {
      return requester<TodoQuery, TodoQueryVariables>(TodoDocument, variables, options) as Promise<TodoQuery>;
    },
    Users(variables?: UsersQueryVariables, options?: C): Promise<UsersQuery> {
      return requester<UsersQuery, UsersQueryVariables>(UsersDocument, variables, options) as Promise<UsersQuery>;
    },
    User(variables: UserQueryVariables, options?: C): Promise<UserQuery> {
      return requester<UserQuery, UserQueryVariables>(UserDocument, variables, options) as Promise<UserQuery>;
    }
  };
}
export type Sdk = ReturnType<typeof getSdk>;