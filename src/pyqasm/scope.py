# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module defining the ScopeManager class for managing variable scopes and contexts.
This class provides methods for pushing/popping scopes and contexts,
checking variable visibility, and updating variable values.
"""

from collections import deque

from pyqasm.elements import Context, Variable


# pylint: disable-next=too-many-public-methods
class ScopeManager:
    """
    Manages variable scopes and contexts for QasmVisitor and PulseVisitor.

    This class provides methods for pushing/popping scopes and contexts,
    checking variable visibility, and updating variable values.
    """

    def __init__(self) -> None:
        """Initialize the ScopeManager with a global scope and context."""
        self._scope: deque = deque([{}])
        self._context: deque = deque([Context.GLOBAL])
        self._scope_level: int = 0

    def push_scope(self, scope: dict) -> None:
        """Push a new scope dictionary onto the scope stack."""
        if not isinstance(scope, dict):
            raise TypeError("Scope must be a dictionary")
        self._scope.append(scope)

    def pop_scope(self) -> None:
        """Pop the top scope dictionary from the scope stack."""
        if len(self._scope) == 0:
            raise IndexError("Scope list is empty, cannot pop")
        self._scope.pop()

    def push_context(self, context: Context) -> None:
        """Push a new context onto the context stack."""
        if not isinstance(context, Context):
            raise TypeError("Context must be an instance of Context")
        self._context.append(context)

    def restore_context(self) -> None:
        """Pop the top context from the context stack."""
        if len(self._context) == 0:
            raise IndexError("Context list is empty, cannot pop")
        self._context.pop()

    def get_parent_scope(self) -> dict:
        """Get the parent scope dictionary."""
        if len(self._scope) < 2:
            raise IndexError("Parent scope not available")
        return self._scope[-2]

    def get_curr_scope(self) -> dict:
        """Get the current scope dictionary."""
        if len(self._scope) == 0:
            raise IndexError("No scopes available to get")
        return self._scope[-1]

    def get_scope_level(self) -> int:
        """Get the current scope level."""
        return self._scope_level

    def increment_scope_level(self) -> None:
        """Increment the current scope level."""
        self._scope_level += 1

    def decrement_scope_level(self) -> None:
        """Decrement the current scope level."""
        if self._scope_level == 0:
            raise ValueError("Cannot decrement scope level below 0")
        self._scope_level -= 1

    def get_curr_context(self) -> Context:
        """Get the current context."""
        if len(self._context) == 0:
            raise IndexError("No context available to get")
        return self._context[-1]

    def get_global_scope(self) -> dict:
        """Get the global scope dictionary."""
        if len(self._scope) == 0:
            raise IndexError("No scopes available to get")
        return self._scope[0]

    def in_global_scope(self) -> bool:
        """Check if currently in the global scope."""
        return len(self._scope) == 1 and self.get_curr_context() == Context.GLOBAL

    def in_function_scope(self) -> bool:
        """Check if currently in a function scope."""
        return len(self._scope) > 1 and self.get_curr_context() == Context.FUNCTION

    def in_gate_scope(self) -> bool:
        """Check if currently in a gate scope."""
        return len(self._scope) >= 1 and self.get_curr_context() == Context.GATE

    def in_block_scope(self) -> bool:
        """Check if currently in a block scope (if/else/for/while)."""
        return len(self._scope) > 1 and self.get_curr_context() == Context.BLOCK

    def check_in_scope(self, var_name: str) -> bool:
        """
        Check if a variable is visible in the current scope.

        Args:
            var_name (str): The name of the variable to check.

        Returns:
            bool: True if the variable is in scope, False otherwise.
        """
        global_scope = self.get_global_scope()
        curr_scope = self.get_curr_scope()
        if self.in_global_scope():
            return var_name in global_scope
        if self.in_function_scope() or self.in_gate_scope():
            if var_name in curr_scope:
                return True
            if var_name in global_scope:
                return global_scope[var_name].is_constant or global_scope[var_name].is_qubit
        if self.in_block_scope():
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    return var_name in scope
                if var_name in scope:
                    return True
        return False

    def check_in_global_scope(self, var_name: str) -> bool:
        """
        Check if a variable is visible in the global scope.

        Args:
            var_name (str): The name of the variable to check.

        Returns:
            bool: True if the variable is in the global scope, False otherwise.
        """
        return var_name in self.get_global_scope()

    def get_from_visible_scope(self, var_name: str) -> Variable | None:
        """
        Retrieve a variable from the visible scope.

        Args:
            var_name (str): The name of the variable to retrieve.

        Returns:
            Variable | None: The variable if found, None otherwise.
        """
        global_scope = self.get_global_scope()
        curr_scope = self.get_curr_scope()
        if self.in_global_scope():
            return global_scope.get(var_name, None)
        if self.in_function_scope() or self.in_gate_scope():
            if var_name in curr_scope:
                return curr_scope[var_name]
            if var_name in global_scope and (
                global_scope[var_name].is_constant or global_scope[var_name].is_qubit
            ):
                # we also need to return the variable if it is a constant or qubit
                # in the global scope, as it can be used in the function or gate
                return global_scope[var_name]
        if self.in_block_scope():
            var_found = None
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    var_found = scope.get(var_name, None)
                    break
                if var_name in scope:
                    return scope[var_name]
            if not var_found:
                # if broken out of the loop without finding the variable,
                # check the global scope
                var_found = global_scope.get(var_name, None)
            return var_found
        return None

    def get_from_global_scope(self, var_name: str) -> Variable | None:
        """
        Retrieve a variable from the global scope.

        Args:
            var_name (str): The name of the variable to retrieve.

        Returns:
            Variable | None: The variable if found, None otherwise.
        """
        return self.get_global_scope().get(var_name, None)

    def add_var_in_scope(self, variable: Variable) -> None:
        """
        Add a variable to the current scope.

        Args:
            variable (Variable): The variable to add.

        Raises:
            ValueError: If the variable already exists in the current scope.
        """
        curr_scope = self.get_curr_scope()
        if variable.name in curr_scope:
            raise ValueError(f"Variable '{variable.name}' already exists in current scope")
        curr_scope[variable.name] = variable

    def update_var_in_scope(self, variable: Variable) -> None:
        """
        Update the variable in the current scope.

        Args:
            variable (Variable): The variable to be updated.

        Raises:
            ValueError: If no scope is available to update.
        """
        if len(self._scope) == 0:
            raise ValueError("No scope available to update")
        global_scope = self.get_global_scope()
        curr_scope = self.get_curr_scope()
        if self.in_global_scope():
            global_scope[variable.name] = variable
        if self.in_function_scope() or self.in_gate_scope():
            curr_scope[variable.name] = variable
        if self.in_block_scope():
            for scope, context in zip(reversed(self._scope), reversed(self._context)):
                if context != Context.BLOCK:
                    scope[variable.name] = variable
                    break
                if variable.name in scope:
                    scope[variable.name] = variable
                    break
                continue
