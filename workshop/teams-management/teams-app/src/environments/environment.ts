export const environment = {
  production: false,
  apiUrl: "http://teams-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/api", // Use proxy path instead of direct URL
  keycloak: {
    url: "http://platform-auth.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io",
    realm: "teams",
    clientId: "teams-ui",
  },
};
