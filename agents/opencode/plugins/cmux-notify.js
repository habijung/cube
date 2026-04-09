export const server = async (ctx) => {
  return {
    event: async ({ event }) => {
      switch (event.type) {
        case "session.idle":
          await ctx.$`cmux notify --title OpenCode --subtitle "Waiting for input"`.nothrow().quiet();
          break;
        case "session.error":
          await ctx.$`cmux notify --title OpenCode --subtitle Error`.nothrow().quiet();
          break;
      }
    },
  };
};
