import { KeycloakConfig } from 'keycloak-js';

const keycloakConfig: KeycloakConfig = {
//  url: 'http://platform-auth.127.0.0.1.sslip.io',
  url: 'http://platform-auth.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/',
  realm: 'teams',
  clientId: 'teams-ui',
};

export default keycloakConfig;
