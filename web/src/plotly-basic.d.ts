declare module "plotly.js-basic-dist" {
  // The basic distribution exposes the same imperative API as `plotly.js`.
  // Re-exporting that types module is enough for our usage.
  import * as Plotly from "plotly.js";
  export = Plotly;
}
