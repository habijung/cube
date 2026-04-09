// cmux-notify: Sends cmux workspace tab notifications on idle/error events.
// - Debounce (500ms): Consolidates rapid event bursts (e.g. Esc cancel: idle→error→idle)
// - Error priority: If any error occurs within the debounce window, error notification wins
// - Error body: Includes error message via --body when available
// - Graceful fallback: .nothrow().quiet() ensures no crash when cmux is not running
//
// References:
// - OpenCode Plugins: https://opencode.ai/docs/en/plugins/
// - Plugin SDK: https://www.npmjs.com/package/@opencode-ai/plugin
// - Event types: node_modules/@opencode-ai/sdk/dist/gen/types.gen.d.ts
// - cmux notify: `cmux notify --help`
export const server = async (ctx) => {
  let timer; // debounce timer
  let hasError = false; // error flag within debounce window
  let errorMessage = ""; // last error message for --body

  return {
    event: async ({ event }) => {
      // Collect events; error sets flag + captures message
      switch (event.type) {
        case "session.idle":
          break;
        case "session.error":
          hasError = true;
          // All error types except MessageOutputLengthError have data.message
          errorMessage = event.properties?.error?.data?.message || "";
          break;
        default:
          return; // ignore unrelated events
      }

      // Reset debounce timer on each event; only the final state fires
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const subtitle = hasError ? "Error" : "Waiting for input";
        const body = hasError ? errorMessage : "";
        hasError = false;
        errorMessage = "";
        if (body) {
          await ctx.$`cmux notify --title OpenCode --subtitle ${subtitle} --body ${body}`.nothrow().quiet();
        } else {
          await ctx.$`cmux notify --title OpenCode --subtitle ${subtitle}`.nothrow().quiet();
        }
      }, 500);
    },
  };
};
