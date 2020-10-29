# vulnerability_crawler_docker
vulnerability crawler docker version

## Source

1. cvedetails_crawler
2. certeu
3. NVD
4. ICSCert
5. mergecve
6. vuldb
7. exploitdb
8. twitter-cve
9. NTISAC
10. HISAC

## Deployment
### cvedetails

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t cvedetails_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name cvedetails_crawler cvedetails_crawler:1.0.0 python3 main.py
```
### certeu

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t certeu_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name certeu_crawler certeu_crawler:1.0.0 python3 main.py
```
### NVD

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t nvd_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name nvd_crawler nvd_crawler:1.0.0 python3 main.py
```

### ICSCert
*Join <strong>ics_cert-alert</strong> channel on slack to see the result.*

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t icscert_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name icscert_crawler icscert_crawler:1.0.0 python3 main.py
```

### mergecve

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t mergecve_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name mergecve_crawler mergecve_crawler:1.0.0 python3 main.py
```
### vuldb

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t vuldb_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name vuldb_crawler vuldb_crawler:1.0.0 python3 main.py
```
### exploitdb

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t exploitdb_crawler:1.0.0 .
```
2. Run container
```bash
	docker run -d --name exploitdb_crawler exploitdb_crawler:1.0.0 python main.py
```
### twitter-cve

1. go to the folder

```bash
	cd twitter-cve
```
2. Build the docker image with docker-compose.yml and run container
```bash
	docker-compose up
```
### NTISAC

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t ntisac_analysis:1.0.0 .
```
2. Run container
```bash
	docker run -d --name ntisac_analysis ntisac_analysis:1.0.0 python3 main.py
```

### HISAC

1. Build the docker image with Dockerfile and given a tag

```bash
	docker build -t hisac_analysis:1.0.0 .
```
2. Run container
```bash
	docker run -d --name hisac_analysis hisac_analysis:1.0.0 python3 main.py
```


## Authors
YuPingAOA


