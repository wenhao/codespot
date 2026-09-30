// Fixture: JS file with known oxlint + eslint(sonarjs) findings.
// Expected rules are listed in tests/fixtures/expected.json (keep in sync).

const config = {
  set credentials(v) {
    this._credentials = v;
  }, // sonarjs: rules on setters? (probe)
};

function handler(req) {
  const response = fx(req); // eval-equivalent? no; probe
  return response;
}

function fx(input) {
  // eslint-disable-next-line
  if (1 == 1) {           // eslint core eqeqeq (warn)
    return input * Math.random();
  }
  const unused = 42;      // sonarjs/no-unused-collection? plain unused -> eslint no-unused-vars + oxlint
  return null;
}

var password = "hunter2"; // sonarjs/hardcoded-credentials? (sonar rule targets specific names)

console.log(config, handler);
