export const server = async (ctx) => {
  let timer;
  let hasError = false;

  return {
    event: async ({ event }) => {
      switch (event.type) {
        case "session.idle":
          break;
        case "session.error":
          hasError = true;
          break;
        default:
          return;
      }

      clearTimeout(timer);
      timer = setTimeout(async () => {
        const subtitle = hasError ? "Error" : "Waiting for input";
        hasError = false;
        await ctx.$`cmux notify --title OpenCode --subtitle ${subtitle}`.nothrow().quiet();
      }, 500);
    },
  };
};
