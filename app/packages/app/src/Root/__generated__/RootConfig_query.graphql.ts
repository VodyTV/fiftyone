/**
 * @generated SignedSource<<7f8e8497095b9097d76934dacf9af779>>
 * @lightSyntaxTransform
 * @nogrep
 */

/* tslint:disable */
/* eslint-disable */
// @ts-nocheck

import { Fragment, ReaderFragment } from "relay-runtime";
export type ColorBy = "field" | "instance" | "label" | "%future added value";
import { FragmentRefs } from "relay-runtime";
export type RootConfig_query$data = {
  readonly config: {
    readonly colorBy: ColorBy;
    readonly colorPool: ReadonlyArray<string>;
    readonly colorscale: string;
    readonly gridZoom: number;
    readonly loopVideos: boolean;
    readonly notebookHeight: number;
    readonly showConfidence: boolean;
    readonly showIndex: boolean;
    readonly showLabel: boolean;
    readonly showTooltip: boolean;
    readonly timezone: string | null;
    readonly useFrameNumber: boolean;
  };
  readonly colorscale: ReadonlyArray<ReadonlyArray<number>> | null;
  readonly " $fragmentType": "RootConfig_query";
};
export type RootConfig_query$key = {
  readonly " $data"?: RootConfig_query$data;
  readonly " $fragmentSpreads": FragmentRefs<"RootConfig_query">;
};

const node: ReaderFragment = (function () {
  var v0 = {
    alias: null,
    args: null,
    kind: "ScalarField",
    name: "colorscale",
    storageKey: null,
  };
  return {
    argumentDefinitions: [],
    kind: "Fragment",
    metadata: null,
    name: "RootConfig_query",
    selections: [
      {
        alias: null,
        args: null,
        concreteType: "AppConfig",
        kind: "LinkedField",
        name: "config",
        plural: false,
        selections: [
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "colorBy",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "colorPool",
            storageKey: null,
          },
          v0 /*: any*/,
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "gridZoom",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "loopVideos",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "notebookHeight",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "showConfidence",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "showIndex",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "showLabel",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "showTooltip",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "timezone",
            storageKey: null,
          },
          {
            alias: null,
            args: null,
            kind: "ScalarField",
            name: "useFrameNumber",
            storageKey: null,
          },
        ],
        storageKey: null,
      },
      v0 /*: any*/,
    ],
    type: "Query",
    abstractKey: null,
  };
})();

(node as any).hash = "85f4c6bc30144f4727c2654f762bc73b";

export default node;