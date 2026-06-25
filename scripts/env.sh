#!/usr/bin/env bash

trim_env_value() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf "%s" "${value}"
}

strip_env_inline_comment() {
  local value="$1"
  local result="" char previous=""
  local in_single=0 in_double=0
  local i

  for ((i = 0; i < ${#value}; i++)); do
    char="${value:i:1}"
    if [[ "${char}" == "'" && "${in_double}" -eq 0 ]]; then
      if [[ "${in_single}" -eq 0 ]]; then in_single=1; else in_single=0; fi
    elif [[ "${char}" == '"' && "${in_single}" -eq 0 ]]; then
      if [[ "${in_double}" -eq 0 ]]; then in_double=1; else in_double=0; fi
    elif [[ "${char}" == "#" && "${in_single}" -eq 0 && "${in_double}" -eq 0 ]]; then
      if [[ -z "${result}" || "${previous}" =~ [[:space:]] ]]; then
        break
      fi
    fi
    result+="${char}"
    previous="${char}"
  done

  trim_env_value "${result}"
}

load_env_file_if_unset() {
  local env_file="${1:-.env}"
  [[ -f "${env_file}" ]] || return 0

  local raw_line line key value
  while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
    line="$(trim_env_value "${raw_line}")"
    [[ -z "${line}" || "${line:0:1}" == "#" || "${line}" != *=* ]] && continue

    key="$(trim_env_value "${line%%=*}")"
    value="$(trim_env_value "${line#*=}")"
    value="$(strip_env_inline_comment "${value}")"
    [[ "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    [[ -z "${!key+x}" ]] || continue

    if [[ ${#value} -ge 2 ]]; then
      if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
        value="${value:1:${#value}-2}"
      elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
        value="${value:1:${#value}-2}"
      fi
    fi
    export "${key}=${value}"
  done < "${env_file}"
}

resolve_api_base_url() {
  local user_api_base_url="$1"
  local user_api_host_set="$2"
  local user_api_port_set="$3"

  if [[ -n "${user_api_base_url}" ]]; then
    printf "%s" "${user_api_base_url}"
  elif [[ -n "${user_api_host_set}" || -n "${user_api_port_set}" ]]; then
    printf "http://%s:%s/api/v1" "${API_HOST}" "${API_PORT}"
  else
    printf "%s" "${API_BASE_URL:-http://${API_HOST}:${API_PORT}/api/v1}"
  fi
}
