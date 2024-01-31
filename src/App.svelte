<script>
  import { Router, Link, Route } from "svelte-routing";
  import Home from "./lib/Home.svelte";
  import Progress from "./lib/Progress.svelte";

  export let url = "";
</script>

<Router {url}>
  <div>
    <Route path="/:id" component={Progress} />
    <Route path="/"><Home /></Route>
  </div>
</Router>
