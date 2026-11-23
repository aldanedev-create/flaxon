# Recipe: a Teloce admin field

A `TeloceField` is a normal validated `Field` with a `.vel` component and an
HTML fallback. Users never need Node: Flaxon compiles the component with the
bundled Teloce toolchain.

```python
from flaxon.admin import Component, TeloceField

RATING = """
<template>
  <select :name="name">
    <option v-for="n in max" :value="n">{{ n }}</option>
  </select>
</template>
<script lang="ts">
export default { props: { name: String, max: { type: Number, default: 5 } } };
</script>
"""

rating = TeloceField(
    "score",
    Component("rating", RATING),
    label="Score",
    fallback="select",
    fallback_choices=[(str(n), str(n)) for n in range(1, 6)],
    props={"max": 5},
)
assert rating.kind == "teloce"
assert rating.clean("4") == "4"
```

The component compiles to browser JavaScript on demand; the fallback keeps the
form usable without JavaScript and keeps server-side validation in Python.
