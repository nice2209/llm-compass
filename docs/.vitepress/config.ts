import { defineConfig } from "vitepress";

// 한국어 기본. 영어 확장 시 locales 키를 추가하면 됨.
export default defineConfig({
  lang: "ko-KR",
  title: "LLM Compass",
  description: "LLM API 종합 가격 비교 + 예산 가드",
  base: "/llm-compass/",
  lastUpdated: true,
  cleanUrls: true,

  head: [
    ["meta", { name: "theme-color", content: "#3b82f6" }],
    ["meta", { property: "og:title", content: "LLM Compass" }],
    [
      "meta",
      {
        property: "og:description",
        content: "주요 LLM API 가격을 한눈에 비교하고 예산을 지키세요.",
      },
    ],
  ],

  themeConfig: {
    nav: [
      { text: "홈", link: "/" },
      { text: "가격 비교", link: "/pricing/" },
      { text: "용도별 추천", link: "/plans/" },
      { text: "llm-guard", link: "/guard/" },
      { text: "GitHub", link: "https://github.com/nice2209/llm-compass" },
    ],

    sidebar: {
      "/pricing/": [
        {
          text: "가격",
          items: [{ text: "가격 비교표", link: "/pricing/" }],
        },
      ],
      "/plans/": [
        {
          text: "추천",
          items: [{ text: "용도별 추천", link: "/plans/" }],
        },
      ],
      "/guard/": [
        {
          text: "llm-guard",
          items: [{ text: "사용법", link: "/guard/" }],
        },
      ],
    },

    socialLinks: [{ icon: "github", link: "https://github.com/nice2209/llm-compass" }],

    footer: {
      message: "Apache 2.0 라이선스로 배포됩니다.",
      copyright: "Copyright © 2026 LLM Compass",
    },

    docFooter: {
      prev: "이전",
      next: "다음",
    },

    outline: { label: "목차" },
    returnToTopLabel: "맨 위로",
    sidebarMenuLabel: "메뉴",
    darkModeSwitchLabel: "테마",
    lightModeSwitchTitle: "라이트 모드로 전환",
    darkModeSwitchTitle: "다크 모드로 전환",

    search: {
      provider: "local",
      options: {
        locales: {
          root: {
            translations: {
              button: { buttonText: "검색", buttonAriaLabel: "검색" },
              modal: {
                noResultsText: "검색 결과가 없습니다",
                resetButtonTitle: "검색 초기화",
                footer: {
                  selectText: "선택",
                  navigateText: "이동",
                  closeText: "닫기",
                },
              },
            },
          },
        },
      },
    },
  },
});
