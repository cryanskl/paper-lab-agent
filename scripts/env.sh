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
  if [[ -L "${env_file}" || ( -e "${env_file}" && ! -f "${env_file}" ) ]]; then
    printf "env file is not a regular file: %s\n" "${env_file}" >&2
    return 1
  fi
  local env_parent="${env_file%/*}"
  local env_parent_cursor="" env_parent_part
  if [[ "${env_parent}" != "${env_file}" ]]; then
    if [[ "${env_parent}" == /* ]]; then
      env_parent_cursor="/"
    fi
    IFS="/" read -ra env_parent_parts <<< "${env_parent}"
    for env_parent_part in "${env_parent_parts[@]}"; do
      [[ -z "${env_parent_part}" || "${env_parent_part}" == "." ]] && continue
      if [[ -z "${env_parent_cursor}" ]]; then
        env_parent_cursor="${env_parent_part}"
      elif [[ "${env_parent_cursor}" == "/" ]]; then
        env_parent_cursor="/${env_parent_part}"
      else
        env_parent_cursor="${env_parent_cursor}/${env_parent_part}"
      fi
      if [[ -L "${env_parent_cursor}" || ( -e "${env_parent_cursor}" && ! -d "${env_parent_cursor}" ) ]]; then
        printf "env file parent is not a regular directory: %s\n" "${env_parent_cursor}" >&2
        return 1
      fi
    done
  fi
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

resolve_connect_host() {
  local bind_host="$1"

  if [[ "${bind_host}" == "0.0.0.0" ]]; then
    printf "127.0.0.1"
  else
    printf "%s" "${bind_host}"
  fi
}

format_url_host() {
  local host="$1"

  if [[ "${host}" == *:* && "${host}" != \[* ]]; then
    printf "[%s]" "${host}"
  else
    printf "%s" "${host}"
  fi
}

resolve_api_base_url() {
  local user_api_base_url="$1"
  local user_api_host_set="$2"
  local user_api_port_set="$3"
  local api_connect_host

  if [[ -n "${user_api_base_url}" ]]; then
    printf "%s" "${user_api_base_url}"
  elif [[ -n "${user_api_host_set}" || -n "${user_api_port_set}" ]]; then
    api_connect_host="$(resolve_connect_host "${API_HOST}")"
    printf "http://%s:%s/api/v1" "$(format_url_host "${api_connect_host}")" "${API_PORT}"
  else
    printf "%s" "${API_BASE_URL:-http://${API_HOST}:${API_PORT}/api/v1}"
  fi
}
