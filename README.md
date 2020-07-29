<h1 align="center">Immuni Backend Analytics Service</h1>

<div align="center">
<img width="256" height="256" src=".github/logo.png">
</div>

<br />

<div align="center">
    <!-- CoC -->
    <a href="CODE_OF_CONDUCT.md">
      <img src="https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg" />
    </a>
    <a href="https://docs.python.org/3/">
      <img alt="Python"
      src="https://img.shields.io/badge/python-3.8-informational">
    </a>
    <a href="https://github.com/psf/black">
      <img alt="Code style: black"
      src="https://img.shields.io/badge/code%20style-black-000000.svg">
    </a>
    <a href="http://mypy-lang.org/">
      <img alt="Checked with mypy"
      src="http://www.mypy-lang.org/static/mypy_badge.svg">
    </a>
    <a href="https://github.com/PyCQA/bandit">
      <img alt="security: bandit"
      src="https://img.shields.io/badge/security-bandit-yellow.svg">
    </a>
</div>

<div align="center">
  <h3>
    </span>
    <a href="https://github.com/immuni-app/immuni-documentation">
      Documentation
    </a>
    <span> | </span>    
    <a href="CONTRIBUTING.md">
      Contributing
    </a>
  </h3>
</div>

# Table of contents

- [Context](#context)
- [Installation](#installation)
- [Contributing](#contributing)
  - [Contributors](#contributors)
- [Licence](#licence)
  - [Authors / Copyright](#authors--copyright)
  - [Third-party component licences](#third-party-component-licences)
  - [Licence details](#licence-details)


# Context
This repository contains the source code of Immuni's Analytics Service. More detailed information about Immuni can be found in the following documents:

- [High-Level Description](https://github.com/immuni-app/documentation/blob/master/README.md)
- [Product Description](https://github.com/immuni-app/documentation/blob/master/Product%20Description.md)
- [Technology Description](https://github.com/immuni-app/documentation/blob/master/Technology%20Description.md)
- [Traffic Analysis Mitigation](https://github.com/immuni-app/immuni-documentation/blob/master/Traffic%20Analysis%20Mitigation.md)

**Please take the time to read and consider the other repositories in full before digging into the source code or opening an Issue. They contain a lot of details that are fundamental to understanding the source code and this repository's documentation.**

# Installation

This backend service comes with an out-of-the-box installation, leveraging [Docker](https://www.docker.com/) containers.
Please ensure that Docker is installed on your computer (docker-compose version >= 1.25.5).

```bash
git clone --recurse-submodules git@github.com:immuni-app/immuni-backend-analytics.git
cd immuni-backend-analytics/docker
docker-compose build \
    --build-arg GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD) \
    --build-arg GIT_SHA=$(git rev-parse --verify HEAD) \
    --build-arg GIT_TAG=$(git tag --points-at HEAD | cat) \
    --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

The backend service can then be launched.

```bash
docker-compose up
```

At this point, the service is available at http://0.0.0.0:5000/swagger.

For more information about how the project is generated and structured, please refer to the [Contributing](#contributing) section below.

# Contributing
Contributions are most welcome. Before proceeding, please read the [Code of Conduct](./CODE_OF_CONDUCT.md) for guidance on how to approach the community and create a positive environment. Additionally, please read our [CONTRIBUTING](./CONTRIBUTING.md) file, which contains guidance on ensuring a smooth contribution process.

The Immuni project is composed of different repositories—one for each component or service. Please use this repository for contributions strictly relevant to Immuni's backend services. To propose a feature request, please open an issue in the [Documentation repository](https://github.com/immuni-app/immuni-documentation). This lets everyone involved see it, consider it, and participate in the discussion. Opening an issue or pull request in this repository may slow down the overall process.

## Contributors
Here is a list of Immuni's contributors. Thank you to everyone involved for improving Immuni, day by day.

<a href="https://github.com/immuni-app/immuni-backend-analytics/graphs/contributors">
  <img
  src="https://contributors-img.web.app/image?repo=immuni-app/immuni-backend-analytics"
  />
</a>

# Licence

## Authors / Copyright

Copyright 2020 (c) Presidenza del Consiglio dei Ministri.

Please check the [AUTHORS](AUTHORS) file for extended reference.

## Third-party component licences

Please see the Technology Description’s [Backend Services Technologies](https://github.com/immuni-app/documentation/blob/master/Technology%20Description.md#backend-services-technologies) section, which also lists the corresponding licences.

## Licence details

The licence for this repository is a [GNU Affero General Public Licence version 3](https://www.gnu.org/licenses/agpl-3.0.html) (SPDX: AGPL-3.0). Please see the [LICENSE](LICENSE) file for full reference.

